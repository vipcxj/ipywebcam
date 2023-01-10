/* eslint-disable @typescript-eslint/no-non-null-assertion */
export function createPeerConnection(): RTCPeerConnection {
  const config = {
    sdpSemantics: 'unified-plan',
    iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }],
  };

  const pc = new RTCPeerConnection(config);

  // register some listeners to help debugging
  pc.addEventListener(
    'icegatheringstatechange',
    () => {
      console.log(`iceGathering -> ${pc.iceGatheringState}`);
    },
    false
  );

  pc.addEventListener(
    'iceconnectionstatechange',
    () => {
      console.log(`iceConnection -> ${pc.iceConnectionState}`);
    },
    false
  );

  pc.addEventListener(
    'signalingstatechange',
    () => {
      console.log(`signaling -> ${pc.signalingState}`);
    },
    false
  );

  return pc;
}

async function waitIceGathering(pc: RTCPeerConnection): Promise<void> {
  return new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') {
      resolve();
    } else {
      const checkState = () => {
        if (pc.iceGatheringState === 'complete') {
          pc.removeEventListener('icegatheringstatechange', checkState);
          resolve();
        }
      };
      pc.addEventListener('icegatheringstatechange', checkState);
    }
  });
}

type MediaKind = 'video' | 'audio';

export async function negotiate(
  pc: RTCPeerConnection,
  offerFunc: (
    offer: RTCSessionDescriptionInit
  ) => Promise<RTCSessionDescriptionInit>,
  codec?: { video?: string; audio?: string }
): Promise<void> {
  let offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  await waitIceGathering(pc);
  offer = pc.localDescription!;
  if (codec) {
    if (codec.audio && codec.audio !== 'default') {
      offer.sdp = sdpFilterCodec('audio', codec.audio, offer.sdp!);
    }
    if (codec.video && codec.video !== 'default') {
      offer.sdp = sdpFilterCodec('video', codec.video, offer.sdp!);
    }
  }
  const remoteOffer = await offerFunc(offer);
  await pc.setRemoteDescription(remoteOffer);
}

function arrayInclude<T>(arr: T[], target: T): boolean {
  return !!~arr.indexOf(target);
}

function sdpFilterCodec(kind: MediaKind, codec: string, realSdp: string) {
  const allowed: number[] = [];
  const rtxRegex = new RegExp('a=fmtp:(\\d+) apt=(\\d+)\\r$');
  const codecRegex = new RegExp('a=rtpmap:([0-9]+) ' + escapeRegExp(codec));
  const videoRegex = new RegExp('(m=' + kind + ' .*?)( ([0-9]+))*\\s*$');

  const lines = realSdp.split('\n');

  let isKind = false;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('m=' + kind + ' ')) {
      isKind = true;
    } else if (lines[i].startsWith('m=')) {
      isKind = false;
    }

    if (isKind) {
      let match = lines[i].match(codecRegex);
      if (match) {
        allowed.push(parseInt(match[1]));
      }

      match = lines[i].match(rtxRegex);
      if (match && arrayInclude(allowed, parseInt(match[2]))) {
        allowed.push(parseInt(match[1]));
      }
    }
  }

  const skipRegex = 'a=(fmtp|rtcp-fb|rtpmap):([0-9]+)';
  let sdp = '';

  isKind = false;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('m=' + kind + ' ')) {
      isKind = true;
    } else if (lines[i].startsWith('m=')) {
      isKind = false;
    }

    if (isKind) {
      const skipMatch = lines[i].match(skipRegex);
      if (skipMatch && !arrayInclude(allowed, parseInt(skipMatch[2]))) {
        continue;
      } else if (lines[i].match(videoRegex)) {
        sdp += lines[i].replace(videoRegex, '$1 ' + allowed.join(' ')) + '\n';
      } else {
        sdp += lines[i] + '\n';
      }
    } else {
      sdp += lines[i] + '\n';
    }
  }

  return sdp;
}

function escapeRegExp(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}
