// Copyright (c) Xiaojing Chen
// Distributed under the terms of the Modified BSD License.

import {
  DOMWidgetModel,
  DOMWidgetView,
  ISerializers,
} from '@jupyter-widgets/base';

import { MODULE_NAME, MODULE_VERSION } from './version';

import { createPeerConnection, negotiate } from './webrtc';

// Import the CSS
import '../css/widget.css';

export class WebCamModel extends DOMWidgetModel {
  defaults() {
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
  render() {
    this.el.classList.add('custom-widget');

    this.value_changed();
    this.model.on('change:value', this.value_changed, this);
  }

  value_changed() {
    this.el.textContent = JSON.stringify(this.model.get('desc'));
  }
}
