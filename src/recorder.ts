import { DOMWidgetView } from '@jupyter-widgets/base';
import LRU from 'lru-cache';

import { BaseModel } from './common';
import { Video } from './video';

type ChannelStaleArgs = {
  channel?: string;
};

type RecorderMsgTypeMap = {
  channel_stale: ChannelStaleArgs;
};

type FetchCallback = (blob: Blob) => void;

interface FetchState {
  callbacks: Array<FetchCallback>;
}

type RefreshCallback = (index?: number, channel?: string) => void;

interface RecorderMeta {
  record_count: number;
  chanels: string[];
}

export class RecorderPlayerModel extends BaseModel<RecorderMsgTypeMap> {
  cache: LRU<string, Blob> = new LRU({
    max: 6,
  });
  fetchStates: Record<string, FetchState> = {};
  meta: RecorderMeta | undefined;
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
      this.meta = undefined;
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

  fetchMeta = async (): Promise<RecorderMeta> => {
    if (this.meta) {
      return this.meta;
    }
    const { content } = await this.send_cmd('fetch_meta', {});
    this.meta = content;
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    return this.meta!;
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
}

type LoadStateCallback = (loading: boolean) => void;

export class RecorderPlayerView extends DOMWidgetView {
  video?: Video;
  index = -1;
  indexSize = 0;
  channel = '';
  channels: string[] = [];
  private loading = false;
  private loadStateOnceCallbacks: LoadStateCallback[] = [];

  constructor(...args: any[]) {
    super(...args);
    this.model.addRefereshCallback((i, c) => {
      if (
        this.index === i &&
        ((!this.channel && !c) || (this.channel && c && this.channel === c))
      ) {
        this.load(undefined, undefined, true);
      }
    });
  }

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

  fetchMeta = async (): Promise<void> => {
    const { record_count = 0, chanels = [] } = await this.model.fetchMeta();
    this.indexSize = record_count;
    this.channels = chanels;
  };

  initVideo = async (): Promise<void> => {
    if (!this.video) {
      this.video = new Video();
      this.video.addIndexSelectHandler((i) => {
        this.load(i, undefined);
      });
      this.video.addChannelSelectHandler((channel) => {
        this.load(undefined, channel, false, true);
      });
      this.video.video.addEventListener('ended', async () => {
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
      this.el.appendChild(this.video.container);
      this.update();
      await this.fetchMeta();
      await this.load(0, '');
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
      await this.fetchMeta();
      try {
        if (this.indexSize > 0) {
          const blob = await this.model.fetchData(index, channel);
          this.video.updateData(blob, resumeTime);
        }
        this.index = index;
        this.channel = channel;
        this.video.updateIndexerSize(this.indexSize);
        this.video.updateIndexerIndex(this.index);
        this.video.updateChannels(this.channels);
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
    this.video?.destroy();
    this.video = undefined;
  }

  model: RecorderPlayerModel;
}
