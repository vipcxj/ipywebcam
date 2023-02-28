import { DOMWidgetView } from '@jupyter-widgets/base';
import LRU from 'lru-cache';

import { BaseModel } from './common';
import { Video } from './video';
import { arrayEqual } from './utils';
import {
  RecorderMsgTypeMap,
  FetchState,
  RefreshCallback,
  RecorderMeta,
} from './types';

export class RecorderPlayerModel extends BaseModel<RecorderMsgTypeMap> {
  cache: LRU<string, Blob> = new LRU({
    max: 10,
  });
  metaCache: LRU<string, RecorderMeta> = new LRU({
    max: 100,
  });
  fetchStates: Record<string, FetchState> = {};
  refresh_callbacks: RefreshCallback[] = [];

  static model_name = 'RecorderPlayerModel';
  static view_name = 'RecorderPlayerView'; // Set to null if no view

  defaults(): Backbone.ObjectHash {
    return {
      ...super.defaults(),
      _model_name: RecorderPlayerModel.model_name,
      _view_name: RecorderPlayerModel.view_name,
      format: 'mp4',
      width: '',
      height: '',
      autoplay: true,
      loop: false,
      controls: true,
      autonext: true,
      selected_index: null,
      selected_channel: null,
      selected_range: [0, 0],
    };
  }

  constructor(...args: any[]) {
    super(...args);
    this.addMessageHandler('channel_stale', (cmdMsg) => {
      const { args = {} } = cmdMsg;
      const { channel } = args;
      if (channel) {
        for (const key of this.cache.keys()) {
          if (key.endsWith(`-${channel}`)) {
            this.cache.delete(key);
          }
        }
      } else {
        this.cache.clear();
      }
      this.triggerRefresh(undefined, channel);
    });
  }

  addRefereshCallback = (callback: RefreshCallback): void => {
    this.refresh_callbacks.push(callback);
  };

  removeRefreshCallback = (callback: RefreshCallback): void => {
    const index = this.refresh_callbacks.indexOf(callback);
    if (index >= 0) {
      this.refresh_callbacks.splice(index, 1);
    }
  };

  triggerRefresh = (index?: number, channel?: string): void => {
    this.refresh_callbacks.forEach((cb) => {
      cb(index, channel);
    });
  };

  createIndexKey = (index: number | undefined | null): string => {
    return index === undefined || index === null ? 'global' : `${index}`;
  };

  fetchMeta = async (
    index: number | undefined | null = undefined
  ): Promise<RecorderMeta> => {
    const key = this.createIndexKey(index);
    const cached = this.metaCache.get(key);
    if (cached) {
      return cached;
    }
    const args: Record<string, any> = {};
    if (index !== undefined) {
      args['index'] = index;
    }
    const { content } = await this.send_cmd('fetch_meta', args);
    this.metaCache.set(key, content);
    return content;
  };

  fetchData = async (index: number, channel: string): Promise<Blob> => {
    const key = channel ? `${index}-${channel}` : `${index}`;
    const cached = this.cache.get(key);
    if (cached) {
      return cached;
    }
    let fetchState: FetchState | undefined = this.fetchStates[key];
    if (!fetchState) {
      fetchState = {
        callbacks: [],
      };
      this.fetchStates[key] = fetchState;
      const { content, buffers } = await this.send_cmd('fetch_data', {
        index,
        channel,
      });
      const { format = this.get('format') } = content;
      const blob = new Blob(buffers, { type: `video/${format}` });
      this.cache.set(key, blob);
      fetchState.callbacks.forEach((callback) => callback(blob));
      delete this.fetchStates[key];
      return blob;
    } else {
      let theResolve: undefined | ((blob: Blob | PromiseLike<Blob>) => void) =
        undefined;
      fetchState.callbacks.push((blob) => {
        if (theResolve) {
          theResolve(blob);
        } else {
          throw new Error(
            'This is impossible! No resovle method found. It seems that the promise is not invoked yet.'
          );
        }
      });
      return new Promise<Blob>((resolve) => {
        theResolve = resolve;
      });
    }
  };

  invalidateMeta = (index: number | undefined | null): void => {
    const key = this.createIndexKey(index);
    this.metaCache.delete(key);
  };

  setMarkers = async (index: number, markers: number[]): Promise<void> => {
    await this.send_cmd('set_markers', { index, markers });
    this.invalidateMeta(index);
  };
}

type LoadStateCallback = (loading: boolean) => void;

export class RecorderPlayerView extends DOMWidgetView {
  video?: Video;
  index = -1;
  indexSize = 0;
  channel = '';
  channels: string[] = [];
  markers?: number[];
  statistics: RecorderMeta['statistics'];
  statistics_meta: RecorderMeta['statistics_meta'];
  private loading = false;
  private loadStateOnceCallbacks: LoadStateCallback[] = [];
  selectedRange: [number, number] = [0, 0];

  constructor(...args: any[]) {
    super(...args);
    this.selectedRange = this.model.get('selected_range');
    this.model.addRefereshCallback((i, c) => {
      if (
        this.index === i &&
        ((!this.channel && !c) || (this.channel && c && this.channel === c))
      ) {
        this.load(undefined, undefined, true);
      }
    });
  }

  isRangeSelected = (): boolean => {
    return this.selectedRange[1] > this.selectedRange[0];
  };

  addLoadStateOnceCallback = (callback: LoadStateCallback): void => {
    this.loadStateOnceCallbacks.push(callback);
  };

  setLoading = (loading: boolean): void => {
    if (this.loading !== loading) {
      this.loading = loading;
      this.loadStateOnceCallbacks.forEach((callback) => callback(loading));
      this.loadStateOnceCallbacks.splice(0, this.loadStateOnceCallbacks.length);
    }
  };

  render(): void {
    super.render();
    this.initVideo();
  }

  fetchMeta = async (index: number | undefined = undefined): Promise<void> => {
    const {
      record_count = 0,
      chanels = [],
      markers,
      statistics,
      statistics_meta,
    } = await this.model.fetchMeta(index);
    this.indexSize = record_count;
    this.channels = chanels;
    this.markers = markers;
    this.statistics = statistics;
    this.statistics_meta = statistics_meta;
  };

  initVideo = async (): Promise<void> => {
    if (!this.video) {
      this.video = new Video();
      this.video.addVideoInitHandler((video) => {
        video.rangeBar.setMarkers(this.markers);
      });
      this.video.addIndexSelectHandler((i) => {
        this.load(i, undefined);
      });
      this.video.addChannelSelectHandler((channel) => {
        this.load(undefined, channel, false, true);
      });
      this.video.rangeBar.addRangeSelectedCallback((range) => {
        this.selectedRange = range;
        if (this.isRangeSelected()) {
          const video = this.video?.video;
          if (video) {
            video.currentTime = range[0];
          }
          this.model.set('selected_index', this.index);
          this.model.set('selected_channel', this.channel);
        } else {
          this.model.set('selected_index', null);
          this.model.set('selected_channel', null);
        }
        this.model.set('selected_range', range);
        this.model.save_changes();
      });
      this.video.rangeBar.addMarkersChangeCallback((markers) => {
        this.markers = markers;
        this.model.setMarkers(this.index, markers);
      });
      this.model.on('change:selected_index', this.onSelectedIndexChange);
      this.model.on('change:selected_channel', this.onSelectedChannelChange);
      this.model.on('change:selected_range', this.onSelectedRangeChange);
      this.video.video.addEventListener('ended', async () => {
        if (this.isRangeSelected()) {
          return;
        }
        const autonext = this.model.get('autonext');
        const loop = this.model.get('loop');
        if (autonext) {
          if (this.index < this.indexSize - 1) {
            this.load(this.index + 1, undefined);
          } else if (this.index === this.indexSize - 1 && loop) {
            this.load(0, undefined);
          }
        }
      });
      this.video.video.addEventListener('timeupdate', () => {
        if (this.isRangeSelected()) {
          const video = this.video?.video;
          if (video) {
            if (video.currentTime >= this.selectedRange[1]) {
              const loop = this.model.get('loop');
              if (loop) {
                video.currentTime = this.selectedRange[0];
              } else {
                video.pause();
              }
            }
          }
        }
      });
      this.el.appendChild(this.video.container);
      this.update();
      await this.load(0, '');
    }
  };

  onSelectedIndexChange = (): void => {
    const index = this.model.get('selected_index');
    if (index !== undefined && index !== null && this.index !== index) {
      this.load(index, undefined);
    }
  };

  onSelectedChannelChange = (): void => {
    const channel = this.model.get('selected_channel');
    if (channel && this.channel !== channel) {
      this.load(undefined, channel);
    }
  };

  onSelectedRangeChange = (): void => {
    const range = this.model.get('selected_range');
    if (!arrayEqual(this.selectedRange, range)) {
      this.selectedRange = range;
      const rangeBar = this.video?.rangeBar;
      if (rangeBar) {
        rangeBar.selectRange(range);
      }
    }
  };

  waitForLoading = async (loading: boolean): Promise<void> => {
    return new Promise((resolve) => {
      if (this.loading === loading) {
        resolve();
      } else {
        this.addLoadStateOnceCallback((state) => {
          if (state === loading) {
            resolve();
          }
        });
      }
    });
  };

  load = async (
    index?: number,
    channel?: string,
    force = false,
    resumeTime = false
  ): Promise<void> => {
    if (this.video) {
      if (typeof index === 'undefined') {
        index = this.index;
      }
      if (typeof channel === 'undefined') {
        channel = this.channel;
      }
      if (this.index === index && this.channel === channel && !force) {
        return;
      }
      await this.waitForLoading(false);
      this.setLoading(true);
      await this.fetchMeta(index);
      try {
        if (this.indexSize > 0) {
          const blob = await this.model.fetchData(index, channel);
          this.video.updateData(blob, resumeTime);
        }
        this.index = index;
        this.channel = channel;
        this.video.rangeBar.unselectRange();
        this.video.updateIndexerSize(this.indexSize);
        this.video.updateIndexerIndex(this.index);
        this.video.updateChannels(this.channels);
        this.video.updateStatistics(this.statistics, this.statistics_meta);
      } catch (e) {
        console.error(e);
      } finally {
        this.setLoading(false);
      }
    }
  };

  updateWidth = (): void => {
    const width = this.model.get('width');
    if (width !== undefined && width.length > 0) {
      this.video?.video.setAttribute('width', width);
    } else {
      this.video?.video.removeAttribute('width');
    }
  };

  updateHeight = (): void => {
    const height = this.model.get('height');
    if (height !== undefined && height.length > 0) {
      this.video?.video.setAttribute('height', height);
    } else {
      this.video?.video.removeAttribute('height');
    }
  };

  updateOtherVideoAttributes = (): void => {
    const video = this.video?.video;
    if (video) {
      video.autoplay = this.model.get('autoplay') ? true : false;
      if (this.model.get('autonext')) {
        video.loop = false;
      } else {
        video.loop = this.model.get('loop') ? true : false;
      }
    }
    this.video?.enableControls(this.model.get('controls'));
  };

  update(): void {
    this.updateWidth();
    this.updateHeight();
    this.updateOtherVideoAttributes();
    return super.update();
  }

  remove(): void {
    this.model.off('change:selected_index', this.onSelectedIndexChange);
    this.model.off('change:selected_channel', this.onSelectedChannelChange);
    this.model.off('change:selected_range', this.onSelectedRangeChange);
    this.video?.destroy();
    this.video = undefined;
  }

  model: RecorderPlayerModel;
}
