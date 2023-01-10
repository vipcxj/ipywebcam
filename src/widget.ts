// Copyright (c) Xiaojing Chen
// Distributed under the terms of the Modified BSD License.

import {
  DOMWidgetModel,
  DOMWidgetView,
  ISerializers,
} from '@jupyter-widgets/base';
import * as Backbone from 'backbone';

import { createPeerConnection, negotiate } from './webrtc';
import { MODULE_NAME, MODULE_VERSION } from './version';

// Import the CSS
import '../css/widget.css';

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
      devices: [],
      device: null,
    };
  }

  // eslint-disable-next-line @typescript-eslint/explicit-module-boundary-types
  constructor(...args: any[]) {
    super(...args);
    this.fetchDevices();
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

  reset_pc = (): void => {
    this.pc = undefined;
    this.client_stream = undefined;
    this.server_stream = undefined;
  };

  close = async (): Promise<void> => {
    const pc = this.pc;
    if (!pc) {
      return;
    }
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
    this.reset_pc();
  };

  fetchDevices = async (): Promise<void> => {
    console.log('fetchDevices');
    let devices = await navigator.mediaDevices.enumerateDevices();
    devices = devices.filter((device) => device.kind === 'videoinput');
    console.log(devices);
    this.set('devices', devices);
    this.save_changes();
  };

  connect = async (
    video: HTMLVideoElement,
    force_new_pc = false
  ): Promise<void> => {
    if (!this.pc) {
      try {
        const pc = createPeerConnection();
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
              this.reset_pc();
            }
          }
        });
        const constraints = {
          audio: false,
          video: true,
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
      } catch (err) {
        console.error(err);
      }
    } else if (force_new_pc) {
      await this.close();
      await this.connect(video, force_new_pc);
    } else {
      this.bindVideo(video);
    }
  };

  bindVideo = (video: HTMLVideoElement): void => {
    if (!this.pc) {
      return;
    }
    if (this.pc.connectionState === 'connected' && this.server_stream) {
      video.srcObject = this.server_stream;
    } else {
      this.pc.addEventListener('track', (evt) => {
        if (evt.track.kind === 'video') {
          console.log('track gotten');
          this.server_stream = evt.streams[0];
          video.srcObject = this.server_stream;
        }
      });
    }
  };
}

export class WebCamView extends DOMWidgetView {
  pc: RTCPeerConnection | undefined;

  render(): any {
    const video = document.createElement('video');
    video.autoplay = true;
    video.playsInline = true;
    this.el.appendChild(video);
    (this.model as WebCamModel).connect(video);
  }
}
