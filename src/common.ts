import { DOMWidgetModel } from '@jupyter-widgets/base';
import { arrayRemove } from './utils';
import { MODULE_NAME, MODULE_VERSION } from './version';

type Args = Record<string, any>;
type MsgTypeMap = Record<string, Args>;

export interface BaseCommandMessage<C extends string, A extends Args> {
  cmd: C;
  id: string;
  args: A;
}

export type MessageHandler<C extends string, A extends Args> = (
  msg: BaseCommandMessage<C, A>,
  buffers?: ArrayBuffer[] | ArrayBufferView[]
) => void;

type MessageHandlers<MM extends MsgTypeMap> = {
  [K in keyof MM & string]?: Array<MessageHandler<K, MM[K]>>;
};

export class BaseModel<MM extends MsgTypeMap> extends DOMWidgetModel {
  messageHandlers: MessageHandlers<MM> = {};

  defaults(): Backbone.ObjectHash {
    return {
      ...super.defaults(),
      _view_module: MODULE_NAME,
      _model_module: MODULE_NAME,
      _view_module_version: MODULE_VERSION,
      _model_module_version: MODULE_VERSION,
    };
  }

  get message_id(): string {
    return this.model_id;
  }

  constructor(...args: any[]) {
    super(...args);
    this.send_cmd = this.send_cmd.bind(this);
    this.on(
      'msg:custom',
      (
        msg: BaseCommandMessage<any, any>,
        buffers?: ArrayBuffer[] | ArrayBufferView[]
      ) => {
        const { id, cmd } = msg;
        if (id && id !== this.message_id) {
          return;
        }
        Object.keys(this.messageHandlers).forEach((key) => {
          if (key === cmd) {
            const handlers = this.messageHandlers[key as MM & string];
            if (handlers) {
              handlers.forEach((handler) => {
                handler(msg, buffers);
              });
            }
          }
        });
      }
    );
  }

  addMessageHandler = <K extends string & keyof MM>(
    cmd: K,
    handler: MessageHandler<K, MM[K]>
  ): void => {
    let handlers = this.messageHandlers[cmd];
    if (!handlers) {
      handlers = this.messageHandlers[cmd] = [];
    }
    handlers.push(handler);
  };

  removeMessageHandler = <K extends string & keyof MM>(
    cmd: K,
    handler: MessageHandler<K, MM[K]>
  ): void => {
    const handlers = this.messageHandlers[cmd];
    if (handlers) {
      // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
      arrayRemove(handlers!, handler);
    }
  };

  async send_cmd(
    cmd: string,
    args: Record<string, any>,
    wait: false
  ): Promise<void>;
  async send_cmd(
    cmd: string,
    args: Record<string, any>,
    wait: true
  ): Promise<{ content: any; buffers?: ArrayBuffer[] | ArrayBufferView[] }>;
  async send_cmd(
    cmd: string,
    args: Record<string, any>
  ): Promise<{ content: any; buffers?: ArrayBuffer[] | ArrayBufferView[] }>;
  async send_cmd(
    cmd: string,
    args: Record<string, any>,
    wait = true
  ): Promise<{
    content: any;
    buffers?: ArrayBuffer[] | ArrayBufferView[];
  } | void> {
    const id = this.message_id;
    if (wait) {
      return new Promise((resolve) => {
        // eslint-disable-next-line @typescript-eslint/no-this-alias
        const self = this;
        this.send({ cmd, id, args }, {});
        function callback(
          {
            ans,
            id: t_id,
            res,
          }: {
            ans: string;
            id: string;
            res: any;
          },
          buffers?: ArrayBuffer[] | ArrayBufferView[]
        ) {
          if (ans === cmd && t_id === id) {
            resolve({ content: res, buffers });
            self.off('msg:custom', callback);
          }
        }
        this.on('msg:custom', callback);
      });
    } else {
      this.send({ cmd, id, args }, {});
    }
  }
}
