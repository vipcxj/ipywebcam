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
  meta: RecorderMeta;
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

  fetchMeta = async (): Promise<RecorderMeta> => {
    if (this.meta) {
      return this.meta;
    }
    const { content } = await this.send_cmd('fetch_meta', {});
    this.meta = content;
    return this.meta;
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
      const blob = new Blob(buffers, { type: format });
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

export class RecorderPlayerView extends DOMWidgetView {
  video?: Video;
  index = -1;
  channel = '';

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

  render(): void {
    super.render();
    this.initVideo();
  }

  initVideo = async (): Promise<void> => {
    if (!this.video) {
      this.video = new Video();
      this.video.addSelectHandler((i) => {
        this.load(i, undefined);
      });
      this.el.appendChild(this.video.container);
      const { record_count = 0, chanels = [] } = await this.model.fetchMeta();
      if (record_count > 0) {
        await this.load(0, chanels.length > 0 ? chanels[0] : '');
      } else {
        this.video.updateIndexerSize(0);
      }
      this.update();
    }
  };

  load = async (
    index?: number,
    channel?: string,
    force = false
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
      const { record_count = 0 } = await this.model.fetchMeta();
      try {
        this.video.updateIndexerSize(record_count);
        const blob = await this.model.fetchData(index, channel);
        this.video.updateData(blob);
        this.index = index;
        this.channel = channel;
        this.video.updateIndexerIndex(this.index);
      } catch (e) {
        console.error(e);
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
    this.video?.video.setAttribute('loop', this.model.get('loop'));
    this.video?.video.setAttribute('autoplay', this.model.get('autoplay'));
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
