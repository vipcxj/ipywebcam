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
    };
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
}

export class WebCamView extends DOMWidgetView {
  pc: RTCPeerConnection | undefined;
  state = 0;

  render(): any {
    const video = document.createElement('video');
    this.el.appendChild(video);
    this.connect(video);
  }

  connect = async (video: HTMLVideoElement): Promise<void> => {
    if (this.state >= 0) {
      try {
        this.state = -1;
        const pc = await createPeerConnection(video);
        const constraints = {
          audio: false,
          video: true,
        };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        stream.getTracks().forEach((track) => {
          pc.addTrack(track, stream);
        });
        await negotiate(pc, (offer) => {
          console.log(offer);
          return new Promise((resolve) => {
            this.model.set('client_desc', offer);
            this.touch();
            this.model.on('change:server_desc', () => {
              resolve(this.model.get('server_desc'));
            });
          });
        });
      } catch (err) {
        console.error(err);
        this.state = 2;
      }
    }
  };
}
