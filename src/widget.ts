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
import { arrayInclude, arrayFind } from './utils';
import { MODULE_NAME, MODULE_VERSION } from './version';

// Import the CSS
import '../css/widget.css';

type State = 'closing' | 'connecting' | 'connected' | 'closed' | 'error';

const supportsSetCodecPreferences: boolean =
  window.RTCRtpTransceiver &&
  'setCodecPreferences' in window.RTCRtpTransceiver.prototype;

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
      constraints: null,
      video_input_devices: [],
      video_input_device: null,
      audio_input_devices: [],
      audio_input_device: null,
      audio_output_devices: [],
      audio_output_device: null,
      video_codecs: [],
      video_codec: null,
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
    this.fetchCodecs();
    this.fetchDevices();
    this.on('change:video_input_device', (...args) => {
      console.log('change:video_input_device');
      console.log(args);
      this.connect(undefined, true, true);
    });
    this.on('change:audio_input_device', (...args) => {
      console.log('change:audio_input_device');
      console.log(args);
      this.connect(undefined, true, true);
    });
    this.on('change:iceServers', () => {
      this.connect(undefined, true, true);
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

  getConstraints = (): MediaStreamConstraints => {
    let { video, audio } = (this.get(
      'constraints'
    ) as MediaStreamConstraints) || { audio: false, video: true };
    const { deviceId: videoId } = this.get('video_input_device') || {};
    const { deviceId: audioId } = this.get('audio_input_device') || {};
    if (audio && audioId) {
      if (typeof audio === 'boolean') {
        audio = {
          deviceId: audioId,
        };
      } else {
        audio.deviceId = audioId;
      }
    }
    if (video && videoId) {
      if (typeof video === 'boolean') {
        video = {
          deviceId: videoId,
        };
      } else {
        video.deviceId = videoId;
      }
    }
    return { video, audio };
  };

  closePeer = async (): Promise<void> => {
    const state = await this.waitForStateIn('closed', 'connected', 'error');
    if (state === 'closed' || state === 'error') {
      return;
    }
    const pc = this.pc;
    if (!pc) {
      this.setState('closed');
      return;
    }
    this.setState('closing');
    try {
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
      this.resetPeer();
      this.setState('closed');
    } catch (err) {
      this.setState('error');
    }
  };

  fetchCodecs = (): void => {
    const codecs = this.getCodecs();
    this.set('video_codecs', codecs);
    this.save_changes();
  };

  fetchDevices = async (): Promise<void> => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    });
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter(
        (device) => device.kind === 'videoinput' && device.deviceId
      );
      this.set('video_input_devices', videoInputs);
      if (videoInputs.length > 0) {
        this.set('video_input_device', videoInputs[0]);
      }
      const audioInputs = devices.filter(
        (device) => device.kind === 'audioinput' && device.deviceId
      );
      this.set('audio_input_devices', audioInputs);
      if (audioInputs.length > 0) {
        this.set('audio_input_device', audioInputs[0]);
      }
      const audioOutputs = devices.filter(
        (device) => device.kind === 'audiooutput' && device.deviceId
      );
      this.set('audio_output_devices', audioOutputs);
      if (audioOutputs.length > 0) {
        this.set('audio_output_device', audioOutputs[0]);
      }
      this.save_changes();
    } finally {
      stream.getTracks().forEach((track) => track.stop());
    }
  };

  getCodecs = (): string[] => {
    if (supportsSetCodecPreferences) {
      const { codecs = [] } = RTCRtpSender.getCapabilities('video') || {};
      return codecs
        .filter(
          (codec) =>
            !arrayInclude(
              ['video/red', 'video/ulpfec', 'video/rtx'],
              codec.mimeType
            )
        )
        .map((codec) => {
          return (codec.mimeType + ' ' + (codec.sdpFmtpLine || '')).trim();
        });
    } else {
      return [];
    }
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

  syncDevice = (track: MediaStreamTrack): void => {
    let curDeviceId: string | undefined;
    if (typeof track.getCapabilities !== 'undefined') {
      curDeviceId = track.getCapabilities().deviceId;
    } else {
      curDeviceId = track.getSettings().deviceId;
    }
    let change = false;
    if (track.kind === 'video') {
      const { deviceId } = this.get('video_input_device') || {};
      if (curDeviceId !== deviceId) {
        const devices: MediaDeviceInfo[] =
          this.get('video_input_devices') || [];
        const device = arrayFind(
          devices,
          ({ deviceId }, ignored) => curDeviceId === deviceId
        );
        this.set('video_input_device', device || null);
        change = true;
      }
    }
    if (track.kind === 'audio') {
      const { deviceId } = this.get('audio_input_device') || {};
      if (curDeviceId !== deviceId) {
        const devices: MediaDeviceInfo[] =
          this.get('audio_input_devices') || [];
        const device = arrayFind(
          devices,
          ({ deviceId }, ignored) => curDeviceId === deviceId
        );
        this.set('audio_input_device', device || null);
        change = true;
      }
    }
    if (change) {
      this.save_changes();
    }
  };

  connect = async (
    video: HTMLVideoElement | undefined,
    force_reconnect = false,
    only_reconnect = false
  ): Promise<void> => {
    const state = await this.waitForStateIn('closed', 'connected', 'error');
    if (state === 'closed' || state === 'error') {
      if (only_reconnect) {
        return;
      }
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
        const stream = await navigator.mediaDevices.getUserMedia(
          this.getConstraints()
        );
        this.client_stream = stream;
        stream.getTracks().forEach((track) => {
          // this.syncDevice(track);
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
    } else if (force_reconnect) {
      await this.closePeer();
      await this.connect(video, force_reconnect);
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

async function attachSinkId(element: HTMLMediaElement, sinkId: string) {
  if (typeof (element as any).sinkId !== 'undefined') {
    if (sinkId) {
      await (element as any).setSinkId(sinkId);
    }
  } else {
    console.warn('Browser does not support output device selection.');
  }
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
    const { deviceId } = this.model.get('audio_output_device') || {};
    attachSinkId(video, deviceId);
    this.model.on('change:audio_output_device', () => {
      const { deviceId } = this.model.get('audio_output_device') || {};
      attachSinkId(video, deviceId);
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
