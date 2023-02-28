export type ChannelStaleArgs = {
  channel?: string;
};

export type RecorderMsgTypeMap = {
  channel_stale: ChannelStaleArgs;
};

export type FetchCallback = (blob: Blob) => void;

export interface FetchState {
  callbacks: Array<FetchCallback>;
}

export type RefreshCallback = (index?: number, channel?: string) => void;

export interface StatisticsMeta {
  y_range?: [number, number];
}

export interface RecorderMeta {
  record_count: number;
  chanels: string[];
  markers?: number[];
  statistics?: Record<string, Array<[number, number]>>;
  statistics_meta?: Record<string, StatisticsMeta>;
}
