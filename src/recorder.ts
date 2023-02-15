import { DOMWidgetView } from '@jupyter-widgets/base';
import LRU from 'lru-cache';

import { BaseModel } from './common';
import { Video } from './video';

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

export class RecorderPlayerModel extends BaseModel<RecorderMsgTypeMap> {
  cache: LRU<string, Blob> = new LRU({
    max: 6,
  });
  fetchStates: Record<string, FetchState> = {};
  meta: any;

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
  }

  fetchMeta = async (): Promise<any> => {
    if (this.meta) {
      return this.meta;
    }
    const { content } = await this.send_cmd('fetch_meta', {});
    this.meta = content;
    return this.meta;
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
  video?: Video;

  render(): void {
    super.render();
    this.initVideo();
  }

  initVideo = async (): Promise<void> => {
    if (!this.video) {
      await this.model.fetchMeta();
      this.video = new Video();
      this.el.appendChild(this.video.container);
      const blob = await this.model.fetchData(0, '');
      this.video.updateData(blob);
      this.update();
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
