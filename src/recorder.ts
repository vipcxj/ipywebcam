import { DOMWidgetView } from '@jupyter-widgets/base';
import LRU from 'lru-cache';

import { BaseModel } from './common';

type FetchDataArgs = {
  index: number;
};

type RecorderMsgTypeMap = {
  fetch_data: FetchDataArgs;
};

type FetchCallback = (blob: Blob) => void;

interface FetchState {
  callbacks: Array<FetchCallback>;
}

function isMain(video: HTMLVideoElement): boolean {
  return (
    video.hasAttribute('__cxj_main__') &&
    video.getAttribute('__cxj_main__') === 'true'
  );
}

function markMain(video: HTMLVideoElement, main: boolean): void {
  video.setAttribute('__cxj_main__', main ? 'true' : 'false');
}

export class RecorderPlayerModel extends BaseModel<RecorderMsgTypeMap> {
  cache: LRU<string, Blob> = new LRU({
    max: 6,
  });
  fetchStates: Record<string, FetchState> = {};

  static model_name = 'RecorderPlayerModel';
  static view_name = 'RecorderPlayerView'; // Set to null if no view

  mainVideo: HTMLVideoElement | undefined = undefined;
  syncedVideos: HTMLVideoElement[] = [];

  defaults(): Backbone.ObjectHash {
    return {
      ...super.defaults(),
      _model_name: RecorderPlayerModel.model_name,
      _view_name: RecorderPlayerModel.view_name,
      format: 'mp4',
      width: '',
      height: '',
      autoplay: true,
      loop: true,
      controls: true,
    };
  }

  constructor(...args: any[]) {
    super(...args);
  }

  markMainVideo = (video: HTMLVideoElement): void => {
    if (this.mainVideo === video) {
      return;
    }
    const newSyncedVideos = this.syncedVideos.filter((v) => v !== video);
    if (this.mainVideo) {
      markMain(this.mainVideo, false);
      newSyncedVideos.push(this.mainVideo);
    }
    markMain(video, true);
    this.mainVideo = video;
    this.syncedVideos = newSyncedVideos;
  };

  fetchData = async (index: number, channel: string): Promise<Blob> => {
    const key = `${index}-${channel}`;
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
  inited = false;

  render(): void {
    super.render();
    (this.luminoWidget || this.pWidget).addClass('jupyter-widgets');
    (this.luminoWidget || this.pWidget).addClass('widget-image');
    this.update();
  }

  initVideo = async (): Promise<void> => {

  };

  updateWidth = (): void => {
    const width = this.model.get('width');
    if (width !== undefined && width.length > 0) {
      this.el.setAttribute('width', width);
    } else {
      this.el.removeAttribute('width');
    }
  };

  updateHeight = (): void => {
    const height = this.model.get('height');
    if (height !== undefined && height.length > 0) {
      this.el.setAttribute('height', height);
    } else {
      this.el.removeAttribute('height');
    }
  };

  updateOtherVideoAttributes = (): void => {
    this.el.loop = this.model.get('loop');
    this.el.autoplay = this.model.get('autoplay');
    this.el.controls = this.model.get('controls');
  };

  update(): void {
    this.updateWidth();
    this.updateHeight();
    this.updateOtherVideoAttributes();
    return super.update();
  }

  preinitialize(): void {
    this.tagName = 'video';
  }

  el: HTMLVideoElement;
}
