export namespace Base {

    /**
     * Class OwtEvent represents a generic Event in the library.
     */
    class OwtEvent {

    }

    /**
     * Event for Stream.
     */
    class StreamEvent extends OwtEvent {
        stream: Stream;
    }

    /**
     * Class MessageEvent represents a message Event in the library.
     */
    class MessageEvent extends OwtEvent {
        message: string;
        /**
         * ID of the remote endpoint who published this stream.
         */
        origin: string;
        /**
         * Values could be "all", "me" in conference mode, or undefined in P2P mode.
         */
        to: string;
    }

    /**
     * Class ErrorEvent represents an error Event in the library.
     */
    class ErrorEvent extends OwtEvent {
        error: Error;
    }

    /**
     * Class MuteEvent represents a mute or unmute event.
     */
    class MuteEvent extends OwtEvent {
        kind: TrackKind;
    }

    /**
     * A shim for EventTarget. Might be changed to EventTarget later.
     */
    class EventDispatcher {

        /**
         * This function registers a callback function as a handler for the
         * corresponding event. It's shortened form is on(eventType, listener). See
         * the event description in the following table.
         * @param eventType Event string.
         * @param listener Callback function.
         */
        addEventListener(eventType: string, listener: Function): void;

        /**
         * This function removes all event listeners for one type.
         * @param eventType Event string.
         */
        clearEventListener(eventType: string): void;

        /**
         * This function removes a registered event listener.
         * @param eventType Event string.
         * @param listener Callback function.
         */
        removeEventListener(eventType: string, listener: Function): void;
    }

    class PublicationSettings {

    }

    /**
     * Kind of tracks to be muted.
     */
    const enum TrackKind {
        /**
         * Audio tracks.
         * @type string
         */
        AUDIO = 'audio',
        /**
         * Video tracks.
         * @type string
         */
        VIDEO = 'video',
        /**
         * Both audio and video tracks.
         * @type string
         */
        AUDIO_AND_VIDEO = 'av',
    }

    /**
     * Transport type enumeration.
     */
    const enum TransportType {
        QUIC = 'quic',
        WEBRTC = 'webrtc',
    }

    /**
     * Represents the transport constraints for publication and subscription.
     */
    class TransportConstraints {
        /**
         * Transport ID. Undefined transport ID results server to assign a new
         * one. It should always be undefined if transport type is webrtc since the
         * webrtc agent of OWT server doesn't support multiple transceivers on a
         * single PeerConnection.
         */
        id?: string;
        /**
         * Transport type for publication and subscription.
         */
        type: TransportType[];
    }

    /**
     * PublishOptions defines options for publishing a Owt.Base.LocalStream.
     */
    interface PublishOptions {
        /**
         * Parameters for audio RtpSender. Publishing with RTCRtpEncodingParameters is an experimental feature. It is subject to change.
         */
        audio?: AudioEncodingParameters[] | RTCRtpEncodingParameters[];
        transport?: TransportConstraints;
        /**
         * Parameters for video RtpSender. Publishing with RTCRtpEncodingParameters is an experimental feature. It is subject to change.
         */
        video?: VideoCodecParameters[] | RTCRtpEncodingParameters[];
    }

    /**
     * Represents the transport settings for publication and subscription.
     */
    class TransportSettings {
        /**
         * Transport ID.
         */
        id: string;
        /**
         * A list of RTCRtpTransceiver associated with the publication or 
         * subscription. It's only available in conference mode when TransportType
         * is webrtc.
         */
        rtpTransceivers?: RTCRtpTransceiver[];
        /**
         * Transport type for publication and subscription.
         */
        type: TransportType;
    }

    /**
     * Publication represents a sender for publishing a stream. It
     * handles the actions on a LocalStream published to a conference.
     * 
     * Events:
     * | Event Name      | Argument Type | Fired when             |
     * | :-------------- | :------------ | :--------------------- |
     * | ended           | Event         | Publication is ended. |
     * | error           | ErrorEvent    | An error occurred on the publication. |
     * | mute            | MuteEvent     | Publication is muted. Client stopped sending audio and/or video data to remote endpoint. |
     * | unmute          | MuteEvent     | Publication is unmuted. Client continued sending audio and/or video data to remote endpoint. |
     * 
     * ended event may not be fired on Safari after calling Publication.stop().
     */
    class Publication extends EventDispatcher {
        id: string;
        /**
         * Transport settings for the publication.
         */
        readonly transport: TransportSettings;

        /**
         * Get stats of underlying PeerConnection.
         */
        getStats(): Promise<RTCStatsReport>;

        /**
         * Stop sending data to remote endpoint.
         * @param kind 
         */
        mute(kind: TrackKind): Promise<void>;

        /**
         * Stop certain publication. Once a subscription is stopped, it cannot be recovered.
         */
        stop(): void;

        /**
         * Continue sending data to remote endpoint.
         * @param kind Kind of tracks to be unmuted.
         */
        unmute(kind: TrackKind): Promise<void>;
    }

    /**
     * Source info about an audio track. Values: 'mic', 'screen-cast',
     * 'file', 'mixed'.
     */
    const enum AudioSourceInfo {
        MIC = 'mic',
        SCREENCAST = 'screen-cast',
        FILE = 'file',
        MIXED = 'mixed',
    }
      
    /**
     *  Source info about a video track. Values: 'camera', 'screen-cast',
     * 'file', 'mixed'.
     */
    const enum VideoSourceInfo {
        CAMERA = 'camera',
        SCREENCAST = 'screen-cast',
        FILE = 'file',
        MIXED = 'mixed',
    }

    /**
     * Information of a stream's source.
     */
    class StreamSourceInfo {
        /**
         * Audio source info or video source info could be undefined if a stream does not have audio/video track.
         * @param audioSourceInfo Audio source info. Accepted values are: "mic", "screen-cast", "file", "mixed" or undefined.
         * @param videoSourceInfo Video source info. Accepted values are: "camera", "screen-cast", "file", "mixed" or undefined.
         * @param dataSourceInfo Indicates whether it is data. Accepted values are boolean.
         */
        constructor(audioSourceInfo?: AudioSourceInfo, videoSourceInfo?: VideoSourceInfo, dataSourceInfo: boolean);
    }

    /**
     * Base class of streams.
     */
    class Stream extends EventDispatcher {
        /**
         * Custom attributes of a stream.
         */
        attributes: object;
        /**
         * This property is deprecated, please use stream instead.
         */
        mediaStream?: MediaStream;
        /**
         * Source info of a stream.
         */
        source: StreamSourceInfo;

        stream?: MediaStream | WebTransportBidirectionalStream;
    }

    /**
     * Stream captured from current endpoint.
     */
    class LocalStream extends Stream {

        id: string;

        /**
         * @param stream Underlying MediaStream.
         * @param sourceInfo Information about stream's source.
         * @param attributes Custom attributes of the stream.
         */
        constructor(stream: MediaStream, sourceInfo: StreamSourceInfo, attributes: object);
    }

    class RemoteStream extends Stream {
        extraCapabilities: Conference.SubscriptionCapabilities;
        id: string;
        origin: string;
        settings: PublicationSettings;
    }

    class AudioCodecParameters {
        channelCount?: number;
        clockRate?: number;
        name: string;
    }

    class VideoCodecParameters {
        name: string;
        profile?: string;
    }

    class Resolution {

        width: number;
        height: number;

        constructor(width: number, height: number);
    }
}

export namespace Conference {

    /**
     * SubscribeOptions defines options for subscribing a Owt.Base.RemoteStream.
     */
    class SubscribeOptions {
        audio?: AudioSubscriptionConstraints;
        transport?: Base.TransportConstraints;
        video?: VideoSubscriptionConstraints;
    }

    class AudioSubscriptionConstraints {
        codecs: Base.AudioCodecParameters[];
    }

    class VideoSubscriptionConstraints {
        /**
         * Only bitrateMultipliers listed in Owt.Conference.VideoSubscriptionCapabilities are allowed.
         */
        bitrateMultiplier?: number;
        /**
         * Codecs accepted. If none of codecs supported by both sides, connection fails. Leave it undefined will use all possible codecs.
         */
        codecs?: Base.VideoCodecParameters[];
        /**
         * Only frameRates listed in Owt.Conference.VideoSubscriptionCapabilities are allowed.
         */
        frameRate?: number;
        /**
         * Only keyFrameIntervals listed in Owt.Conference.VideoSubscriptionCapabilities are allowed.
         */
        keyFrameInterval?: number;
        /**
         * Only resolutions listed in Owt.Conference.VideoSubscriptionCapabilities are allowed.
         */
        resolution?: Base.Resolution;
        /**
         * Restriction identifier to identify the RTP Streams within an RTP session. When rid is specified, other constraints will be ignored.
         */
        rid?: number;
    }

    class AudioSubscriptionCapabilities {
        codecs: Array<Base.AudioCodecParameters>;
    }

    class VideoSubscriptionCapabilities {
        bitrateMultipliers: number[];
        codecs: Base.VideoCodecParameters[];
        frameRates: number[];
        keyFrameIntervals: number[];
        resolutions: Base.Resolution[]
    }

    class SubscriptionCapabilities {
        audio?: AudioSubscriptionCapabilities;
        video?: VideoSubscriptionCapabilities;
    }

    class ConferenceClientConfiguration {
        rtcConfiguration?: RTCConfiguration;
        webTransportConfiguration?: WebTransportOptions
    }

    class SioSignaling extends Base.EventDispatcher {
        _clearReconnectionTask(): void;
        _onReconnectionTicket(ticketString: string): void;
    }

    /**
     * VideoSubscriptionUpdateOptions defines options for updating a subscription's video part.
     */
    class VideoSubscriptionUpdateOptions {
        /**
         * Only bitrateMultipliers listed in VideoSubscriptionCapabilities are allowed.
         */
        bitrateMultipliers?: number;
        /**
         * Only frameRates listed in VideoSubscriptionCapabilities are allowed.
         */
        frameRate?: number;
        /**
         * Only keyFrameIntervals listed in VideoSubscriptionCapabilities are allowed.
         */
        keyFrameInterval?: number;
        /**
         * Only resolutions listed in VideoSubscriptionCapabilities are allowed.
         */
        resolution?: Base.Resolution;
    }

    /**
     * SubscriptionUpdateOptions defines options for updating a subscription.
     */
    class SubscriptionUpdateOptions {
        video?: VideoSubscriptionUpdateOptions;
    }

    /**
     * Subscription is a receiver for receiving a stream.
     * 
     * Events:
     * | Event Name      | Argument Type | Fired when             |
     * | :-------------- | :------------ | :--------------------- |
     * | ended           | Event         | Subscription is ended. |
     * | error           | ErrorEvent    | An error occurred on the subscription. |
     * | mute            | MuteEvent     | Publication is muted. Remote side stopped sending audio and/or video data. |
     * | unmute          | MuteEvent     | Publication is unmuted. Remote side continued sending audio and/or video data. |
     */
    class Subscription extends Base.EventDispatcher {
        id: string;
        stream: MediaStream | BidirectionalStream;

        /**
         * Update subscription with given options.
         * @param options Subscription update options.
         */
        applyOptions(options: SubscriptionUpdateOptions): Promise<void>;

        /**
         * Get stats of underlying PeerConnection.
         */
        getStats(): Promise<RTCStatsReport>;

        /**
         * Stop reeving data from remote endpoint.
         * @param kind Kind of tracks to be muted.
         */
        mute(kind: Base.TrackKind): Promise<void>;

        /**
         * Stop certain subscription. Once a subscription is stopped, it cannot be recovered.
         */
        stop(): void;

        /**
         * Continue reeving data from remote endpoint.
         * @param kind Kind of tracks to be unmuted.
         */
        unmute(kind: Base.TrackKind): Promise<void>;
    }

    /**
     * The ConferenceClient handles PeerConnections between client and server. For conference controlling, please refer to REST API guide.
     * 
     * Events:
     * | Event Name         | Argument Type                   | Fired when             |
     * | :----------------- | :------------------------------ | :--------------------- |
     * | streamadded        | Owt.Base.StreamEvent            | A new stream is available in the conference. |
     * | participantjoined  | Owt.Conference.ParticipantEvent | A new participant joined the conference. |
     * | messagereceived    | Owt.Base.MessageEvent           | A new message is received. |
     * | serverdisconnected | Owt.Base.OwtEvent               | Disconnected from conference server. |
     * 
     */
    class ConferenceClient extends Base.EventDispatcher {
        constructor();
        /**
         * 
         * @param config Signaling channel implementation for ConferenceClient. SDK uses default signaling channel implementation if this parameter is undefined. Currently, a Socket.IO signaling channel implementation was provided as ics.conference.SioSignaling. However, it is not recommended to directly access signaling channel or customize signaling channel for ConferenceClient as this time.
         */
        constructor(config?: ConferenceClientConfiguration);
        /**
         * 
         * @param config Configuration for ConferenceClient.
         * @param signalingImpl Signaling channel implementation for ConferenceClient. SDK uses default signaling channel implementation if this parameter is undefined. Currently, a Socket.IO signaling channel implementation was provided as ics.conference.SioSignaling. However, it is not recommended to directly access signaling channel or customize signaling channel for ConferenceClient as this time.
         */
        constructor(config?: ConferenceClientConfiguration, signalingImpl: SioSignaling);

        /**
         * Join a conference.
         * @param tokenString Token is issued by conference server(nuve).
         * @returns Return a promise resolved with current conference's information if successfully join the conference. Or return a promise rejected with a newly created Owt.Error if failed to join the conference.
         */
        join(tokenString: string): Promise<ConferenceInfo>;
        /**
         * Leave a conference.
         * @returns Returned promise will be resolved with undefined once the connection is disconnected.
         */
        leave(): Promise<void>;

        /**
         * Publish a LocalStream to conference server. Other participants will be able to subscribe this stream when it is successfully published.
         * @param stream The stream to be published.
         * @param options If options is a PublishOptions, the stream will be published as options specified. If options is a list of RTCRtpTransceivers, each track in the first argument must have a corresponding RTCRtpTransceiver here, and the track will be published with the RTCRtpTransceiver associated with it.
         * @param videoCodecs Video codec names for publishing. Valid values are 'VP8', 'VP9' and 'H264'. This parameter only valid when the second argument is PublishOptions and options.video is RTCRtpEncodingParameters. Publishing with RTCRtpEncodingParameters is an experimental feature. This parameter is subject to change.
         * @returns Returned promise will be resolved with a newly created Publication once specific stream is successfully published, or rejected with a newly created Error if stream is invalid or options cannot be satisfied. Successfully published means PeerConnection is established and server is able to process media data.
         */
        publish(stream: Base.LocalStream, options: Base.PublishOptions | RTCRtpTransceiver[], videoCodecs: string[]): Promise<Base.Publication>;

        /**
         * Send a text message to a participant or all participants.
         * @param message Message to be sent.
         * @param participantId Receiver of this message. Message will be sent to all participants if participantId is undefined.
         */
        send(message: string, participantId: string): Promise<void>;

        /**
         * Subscribe a RemoteStream from conference server.
         * @param stream The stream to be subscribed.
         * @param options Options for subscription.
         */
        subscribe(stream: Base.RemoteStream, options: SubscribeOptions): Promise<Subscription>;

        addEventListener(eventType: 'streamadded', listener: (evt: Base.StreamEvent) => any): void;
        addEventListener(eventType: 'participantjoined', listener: (evt: ParticipantEvent) => any): void;
        addEventListener(eventType: 'messagereceived', listener: (evt: Base.MessageEvent) => any): void;
        addEventListener(eventType: 'serverdisconnected', listener: (evt: Base.OwtEvent) => any): void;

        clearEventListener(eventType: 'streamadded' | 'participantjoined' | 'messagereceived' | 'serverdisconnected'): void;

        removeEventListener(eventType: 'streamadded', listener: (evt: Base.StreamEvent) => any): void;
        removeEventListener(eventType: 'participantjoined', listener: (evt: ParticipantEvent) => any): void;
        removeEventListener(eventType: 'messagereceived', listener: (evt: Base.MessageEvent) => any): void;
        removeEventListener(eventType: 'serverdisconnected', listener: (evt: Base.OwtEvent) => any): void;
    }

    /**
     * The Participant defines a participant in a conference.
     * 
     * Events:
     * | Event Name         | Argument Type                   | Fired when             |
     * | :----------------- | :------------------------------ | :--------------------- |
     * | left               | Owt.Base.OwtEvent               | The participant left the conference. |
     */
    class Participant extends Base.EventDispatcher {
        /**
         * The ID of the participant. It varies when a single user join different conferences.
         */
        id :string;
        role :string;
        /**
         * The user ID of the participant. It can be integrated into existing account management system.
         */
        userId :string;

        addEventListener(eventType: 'left', listener: (evt: Base.OwtEvent) => any): void;
        clearEventListener(eventType: 'left'): void;
        removeEventListener(eventType: 'left', listener: (evt: Base.OwtEvent) => any): void;
    }

    /**
     * Class ParticipantEvent represents a participant event.
     */
    class ParticipantEvent extends Base.OwtEvent {
        participant: Participant;
    }

    /**
     * Information for a conference.
     */
    class ConferenceInfo {
        /**
         * Conference ID. (Room id)
         */
        id: string;
        /**
         * Participants in the conference.
         */
        participants: Array<Participant>;
        /**
         * Streams published by participants. It also includes streams published by current user.
         */
        remoteStreams: Base.RemoteStream[];

        self: Participant;
    }
}