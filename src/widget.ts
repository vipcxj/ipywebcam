// Copyright (c) Xiaojing Chen
// Distributed under the terms of the Modified BSD License.

import {
  DOMWidgetModel,
  DOMWidgetView,
  ISerializers,
} from '@jupyter-widgets/base';
import Backbone from 'backbone';

import {
  createPeerConnection,
  negotiate,
  waitForConnectionState,
} from './webrtc';
import { MODULE_NAME, MODULE_VERSION } from './version';

// Import the CSS
import '../css/widget.css';

type State = 'closing' | 'connecting' | 'connected' | 'closed' | 'error';

export class WebCamModel extends DOMWidgetModel {
  defaults(): Backbone.ObjectHash {
    return {
      ...super.defaults(),
      _model_name: WebCamModel.model_name,
      _model_module: WebCamModel.model_module,
      _model_module_version: WebCamModel.model_module_version,
      _view_name: WebCamModel.view_name,
      _view_module: WebCamModel.view_module,
      _view_module_version: WebCamModel.view_module_version,
      server_desc: null,
      client_desc: null,
      iceServers: [],
      devices: [],
      device: null,
      state: 'closed',
      autoplay: true,
      controls: true,
      crossOrigin: 'not-support',
      width: null,
      height: null,
      playsInline: true,
      muted: false,
    };
  }

  // eslint-disable-next-line @typescript-eslint/explicit-module-boundary-types
  constructor(...args: any[]) {
    super(...args);
    this.fetchDevices();
    this.on('change:device', () => {
      this.connect(undefined, true);
    });
    this.on('change:iceServers', () => {
      this.connect(undefined, true);
    });
  }

  static serializers: ISerializers = {
    ...DOMWidgetModel.serializers,
    // Add any extra serializers here
  };

  static model_name = 'WebCamModel';
  static model_module = MODULE_NAME;
  static model_module_version = MODULE_VERSION;
  static view_name = 'WebCamView'; // Set to null if no view
  static view_module = MODULE_NAME; // Set to null if no view
  static view_module_version = MODULE_VERSION;

  pc: RTCPeerConnection | undefined;
  client_stream: MediaStream | undefined;
  server_stream: MediaStream | undefined;

  resetPeer = (): void => {
    this.pc = undefined;
    this.client_stream = undefined;
    this.server_stream = undefined;
  };

  waitForStateWhen = async (
    checker: (state: State) => boolean
  ): Promise<State> => {
    return new Promise<State>((resolve) => {
      const state: State = this.get('state');
      if (checker(state)) {
        resolve(state);
      } else {
        const checkState = () => {
          const state: State = this.get('state');
          if (checker(state)) {
            this.off('change:state', checkState);
            resolve(state);
          }
        };
        this.on('change:state', checkState);
      }
    });
  };

  waitForStateIn = async (...states: State[]): Promise<State> => {
    return this.waitForStateWhen((state) => states.indexOf(state) !== -1);
  };

  getState = (): State => this.get('state');

  setState = (state: State): void => {
    this.set('state', state);
  };

  closePeer = async (): Promise<void> => {
    const state = await this.waitForStateIn('closed', 'connected', 'error');
    const pc = this.pc;
    if (!pc || state === 'closed' || state === 'error') {
      return;
    }
    this.setState('closing');
    try {
      this.resetPeer();
      pc.close();
      if (pc.connectionState !== 'closed') {
        await new Promise<void>((resolve) => {
          pc.addEventListener('connectionstatechange', () => {
            if (pc.connectionState === 'closed') {
              resolve();
            }
          });
        });
      }
      this.setState('closed');
    } catch (err) {
      this.setState('error');
    }
  };

  fetchDevices = async (): Promise<void> => {
    console.log('fetchDevices');
    let devices = await navigator.mediaDevices.enumerateDevices();
    devices = devices.filter((device) => device.kind === 'videoinput');
    console.log(devices);
    this.set('devices', devices);
    this.save_changes();
  };

  getPeerConfig = (): RTCConfiguration => {
    const config: RTCConfiguration = {};
    const iceServers: any[] = this.get('iceServers');
    if (iceServers && iceServers.length > 0) {
      config.iceServers = iceServers.map((server) => {
        if (typeof server === 'string') {
          return { urls: server };
        } else {
          return server as RTCIceServer;
        }
      });
    }
    return config;
  };

  connect = async (
    video: HTMLVideoElement | undefined,
    force_new_pc = false
  ): Promise<void> => {
    const state = await this.waitForStateIn('closed', 'connected', 'error');
    if (state === 'closed' || state === 'error') {
      try {
        this.setState('connecting');
        const pc = createPeerConnection(this.getPeerConfig());
        this.pc = pc;
        this.bindVideo(video);
        pc.addEventListener('connectionstatechange', () => {
          const state = pc.connectionState;
          if (
            state === 'failed' ||
            state === 'disconnected' ||
            state === 'closed'
          ) {
            pc.close();
            if (this.pc === pc) {
              this.resetPeer();
            }
          }
        });
        pc.addEventListener('track', (evt) => {
          if (evt.track.kind === 'video') {
            console.log('track gotten');
            this.server_stream = evt.streams[0];
          }
        });
        const device = this.get('device');
        const constraints = {
          audio: false,
          video: device ? { deviceId: device.deviceId } : true,
        };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        this.client_stream = stream;
        stream.getTracks().forEach((track) => {
          pc.addTrack(track, stream);
        });
        await negotiate(pc, (offer) => {
          console.log(offer);
          return new Promise((resolve) => {
            this.set('client_desc', offer);
            this.save_changes();
            this.on('change:server_desc', () => {
              resolve(this.get('server_desc'));
            });
          });
        });
        const pcState = await waitForConnectionState(
          pc,
          (state) => state !== 'connecting' && state !== 'new'
        );
        if (pcState === 'connected') {
          this.setState('connected');
        } else {
          await this.closePeer();
        }
      } catch (err) {
        this.setState('error');
        console.error(err);
      }
    } else if (force_new_pc) {
      await this.closePeer();
      await this.connect(video, force_new_pc);
    } else {
      this.bindVideo(video);
    }
  };

  bindVideo = (video: HTMLVideoElement | undefined): void => {
    const pc = this.pc;
    if (!pc || !video) {
      return;
    }
    if (pc.connectionState === 'connected' && this.server_stream) {
      video.srcObject = this.server_stream;
    } else {
      const handler = (evt: RTCTrackEvent): any => {
        if (evt.track.kind === 'video') {
          console.log('track gotten');
          this.server_stream = evt.streams[0];
          video.srcObject = this.server_stream;
          pc.removeEventListener('track', handler);
        }
      };
      pc.addEventListener('track', handler);
    }
  };
}

export class WebCamView extends DOMWidgetView {
  pc: RTCPeerConnection | undefined;

  render(): any {
    const video = document.createElement('video');
    video.playsInline = true;
    this.el.appendChild(video);
    (this.model as WebCamModel).connect(video);
    this.model.on('change:state', () => {
      const model = this.model as WebCamModel;
      if (model.getState() === 'connected') {
        model.connect(video);
      }
    });
    video.autoplay = this.model.get('autoplay');
    this.model.on('change:autoplay', () => {
      video.autoplay = this.model.get('autoplay');
    });
    video.controls = this.model.get('controls');
    this.model.on('change:controls', () => {
      video.controls = this.model.get('controls');
    });
    const width = this.model.get('width');
    if (width) {
      video.width = width;
    }
    this.model.on('change:width', () => {
      const width = this.model.get('width');
      if (width) {
        video.width = width;
      }
    });
    const height = this.model.get('height');
    if (height) {
      video.height = height;
    }
    this.model.on('change:height', () => {
      const height = this.model.get('height');
      if (height) {
        video.height = height;
      }
    });
    video.playsInline = this.model.get('playsInline');
    this.model.on('change:playsInline', () => {
      video.playsInline = this.model.get('playsInline');
    });
    video.muted = this.model.get('muted');
    this.model.on('change:muted', () => {
      video.muted = this.model.get('muted');
    });
    const crossOrigin = this.model.get('crossOrigin');
    if (crossOrigin === 'not-support') {
      video.crossOrigin = null;
    } else {
      video.crossOrigin = crossOrigin;
    }
    this.model.on('change:crossOrigin', () => {
      const crossOrigin = this.model.get('crossOrigin');
      if (crossOrigin === 'not-support') {
        video.crossOrigin = null;
      } else {
        video.crossOrigin = crossOrigin;
      }
    });
  }
}
