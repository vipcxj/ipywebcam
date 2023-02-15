/* eslint-disable @typescript-eslint/no-non-null-assertion */

import '../css/video.css';

const svgNS = 'http://www.w3.org/2000/svg';
const prefix = 'ipywebcam-video-';
export function makeId(id: string): string {
  return `${prefix}${id}`;
}

function createSymbol(
  id: string,
  pathD: string,
  viewBox = '0 0 24 24'
): SVGSymbolElement {
  const symbol = document.createElementNS(svgNS, 'symbol');
  symbol.id = makeId(id);
  symbol.setAttribute('viewBox', viewBox);
  const path = document.createElementNS(svgNS, 'path');
  path.setAttribute('d', pathD);
  symbol.appendChild(path);
  return symbol;
}

function createControlsSvg(): SVGSVGElement {
  const svg = document.createElementNS(svgNS, 'svg');
  svg.id = makeId('icons');
  svg.setAttribute('style', 'display: none');
  const defs = document.createElementNS(svgNS, 'defs');
  svg.appendChild(defs);
  defs.appendChild(
    createSymbol(
      'pause',
      'M14.016 5.016h3.984v13.969h-3.984v-13.969zM6 18.984v-13.969h3.984v13.969h-3.984z'
    )
  );
  defs.appendChild(
    createSymbol('play-icon', 'M8.016 5.016l10.969 6.984-10.969 6.984v-13.969z')
  );
  defs.appendChild(
    createSymbol(
      'volume-high',
      'M14.016 3.234q3.047 0.656 5.016 3.117t1.969 5.648-1.969 5.648-5.016 3.117v-2.063q2.203-0.656 3.586-2.484t1.383-4.219-1.383-4.219-3.586-2.484v-2.063zM16.5 12q0 2.813-2.484 4.031v-8.063q1.031 0.516 1.758 1.688t0.727 2.344zM3 9h3.984l5.016-5.016v16.031l-5.016-5.016h-3.984v-6z'
    )
  );
  defs.appendChild(
    createSymbol(
      'volume-low',
      'M5.016 9h3.984l5.016-5.016v16.031l-5.016-5.016h-3.984v-6zM18.516 12q0 2.766-2.531 4.031v-8.063q1.031 0.516 1.781 1.711t0.75 2.32z'
    )
  );
  defs.appendChild(
    createSymbol(
      'volume-mute',
      'M12 3.984v4.219l-2.109-2.109zM4.266 3l16.734 16.734-1.266 1.266-2.063-2.063q-1.547 1.313-3.656 1.828v-2.063q1.172-0.328 2.25-1.172l-4.266-4.266v6.75l-5.016-5.016h-3.984v-6h4.734l-4.734-4.734zM18.984 12q0-2.391-1.383-4.219t-3.586-2.484v-2.063q3.047 0.656 5.016 3.117t1.969 5.648q0 2.203-1.031 4.172l-1.5-1.547q0.516-1.266 0.516-2.625zM16.5 12q0 0.422-0.047 0.609l-2.438-2.438v-2.203q1.031 0.516 1.758 1.688t0.727 2.344z'
    )
  );
  defs.appendChild(
    createSymbol(
      'fullscreen',
      'M14.016 5.016h4.969v4.969h-1.969v-3h-3v-1.969zM17.016 17.016v-3h1.969v4.969h-4.969v-1.969h3zM5.016 9.984v-4.969h4.969v1.969h-3v3h-1.969zM6.984 14.016v3h3v1.969h-4.969v-4.969h1.969z'
    )
  );
  defs.appendChild(
    createSymbol(
      'fullscreen-exit',
      'M15.984 8.016h3v1.969h-4.969v-4.969h1.969v3zM14.016 18.984v-4.969h4.969v1.969h-3v3h-1.969zM8.016 8.016v-3h1.969v4.969h-4.969v-1.969h3zM5.016 15.984v-1.969h4.969v4.969h-1.969v-3h-3z'
    )
  );
  defs.appendChild(
    createSymbol(
      'pip',
      'M21 19.031v-14.063h-18v14.063h18zM23.016 18.984q0 0.797-0.609 1.406t-1.406 0.609h-18q-0.797 0-1.406-0.609t-0.609-1.406v-14.016q0-0.797 0.609-1.383t1.406-0.586h18q0.797 0 1.406 0.586t0.609 1.383v14.016zM18.984 11.016v6h-7.969v-6h7.969z'
    )
  );
  return svg;
}

export function createSelectiveUses(
  active: string,
  ...ids: string[]
): SVGSVGElement {
  const svg = document.createElementNS(svgNS, 'svg');
  ids.forEach((id) => {
    const use = document.createElementNS(svgNS, 'use');
    use.classList.add(`use-${id}`);
    use.setAttribute('href', `#${makeId(id)}`);
    if (id !== active) {
      use.classList.add('hidden');
    }
    svg.appendChild(use);
  });
  return svg;
}

export function createPlaybackAnimation(): HTMLDivElement {
  const div = document.createElement('div');
  div.id = makeId('playback-animation');
  div.className = 'playback-animation';
  const svg = createSelectiveUses('pause', 'play-icon', 'pause');
  svg.classList.add('playback-icons');
  div.appendChild(svg);
  return div;
}

export function createVideoProgress(): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('video-progress');
  const progress = document.createElement('progress');
  progress.id = makeId('progress-bar');
  progress.classList.add('progress-bar');
  progress.value = progress.max = 0;
  const input = document.createElement('input');
  input.id = makeId('seek');
  input.classList.add('seek');
  input.type = 'range';
  input.value = '0';
  input.min = '0';
  input.step = '1';
  const tooltip = document.createElement('div');
  tooltip.id = makeId('seek-tooltip');
  tooltip.classList.add('seek-tooltip');
  tooltip.innerText = '00:00';
  container.appendChild(progress);
  container.appendChild(input);
  container.appendChild(tooltip);
  return container;
}

function createPlaybackButton(
  options: NormaledVideoOptions
): HTMLButtonElement {
  const button = document.createElement('button');
  button.id = makeId('play');
  button.classList.add('play');
  button.setAttribute(
    'data-title',
    `Play (${descShortcut(options.shortcuts.play)})`
  );
  const svg = createSelectiveUses('play-icon', 'play-icon', 'pause');
  svg.classList.add('playback-icons');
  button.appendChild(svg);
  return button;
}

function createVolumeButton(options: NormaledVideoOptions): HTMLButtonElement {
  const button = document.createElement('button');
  button.id = makeId('volume-button');
  button.classList.add('volume-button');
  button.setAttribute(
    'data-title',
    `Mute (${descShortcut(options.shortcuts.mute)})`
  );
  const svg = createSelectiveUses(
    'volume-high',
    'volume-mute',
    'volume-low',
    'volume-high'
  );
  svg.classList.add('volume-icons');
  button.appendChild(svg);
  return button;
}

function createVolumeInput(): HTMLInputElement {
  const input = document.createElement('input');
  input.id = makeId('volume');
  input.classList.add('volume');
  input.value = '1';
  input.type = 'range';
  input.min = '0';
  input.max = '1';
  input.step = '0.01';
  input.setAttribute('data-mute', '0.5');
  return input;
}

function createVolumeControls(options: NormaledVideoOptions): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('volume-controls');
  const button = createVolumeButton(options);
  container.appendChild(button);
  const input = createVolumeInput();
  container.appendChild(input);
  return container;
}

function createTime(): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('time');
  const elapsed = document.createElement('time');
  elapsed.id = makeId('time-elapsed');
  elapsed.classList.add('time-elapsed');
  elapsed.innerText = '00:00';
  container.appendChild(elapsed);
  const duration = document.createElement('time');
  duration.id = makeId('duration');
  duration.classList.add('duration');
  duration.innerText = '00:00';
  container.appendChild(duration);
  return container;
}

function createLeftControls(options: NormaledVideoOptions): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('left-controls');
  const playbackButton = createPlaybackButton(options);
  container.appendChild(playbackButton);
  const volumeControls = createVolumeControls(options);
  container.appendChild(volumeControls);
  const time = createTime();
  container.appendChild(time);
  return container;
}

function createPipButton(options: NormaledVideoOptions): HTMLButtonElement {
  const button = document.createElement('button');
  button.id = makeId('pip-button');
  button.classList.add('pip-button');
  if (!isPipEnabled()) {
    button.classList.add('hidden');
  }
  button.setAttribute(
    'data-title',
    `PIP (${descShortcut(options.shortcuts.pip)})`
  );
  const svg = createSelectiveUses('pip', 'pip');
  button.appendChild(svg);
  return button;
}

function createFullscreenButton(
  options: NormaledVideoOptions
): HTMLButtonElement {
  const button = document.createElement('button');
  button.id = makeId('fullscreen-button');
  button.classList.add('fullscreen-button');
  button.setAttribute(
    'data-title',
    `Full screen (${descShortcut(options.shortcuts.fullscreen)})`
  );
  const svg = createSelectiveUses(
    'fullscreen',
    'fullscreen',
    'fullscreen-exit'
  );
  button.appendChild(svg);
  return button;
}

function createRightControls(options: NormaledVideoOptions): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('right-controls');
  const pipButton = createPipButton(options);
  container.appendChild(pipButton);
  const fullscreenButton = createFullscreenButton(options);
  container.appendChild(fullscreenButton);
  return container;
}

function createBottomControls(options: NormaledVideoOptions): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('bottom-controls');
  const leftControls = createLeftControls(options);
  container.appendChild(leftControls);
  const rightControls = createRightControls(options);
  container.appendChild(rightControls);
  return container;
}

function createVideoControls(options: NormaledVideoOptions): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('video-controls');
  const videoProgress = createVideoProgress();
  container.appendChild(videoProgress);
  const bottomControls = createBottomControls(options);
  container.appendChild(bottomControls);
  return container;
}

const VIDEO_WORKS = !!document.createElement('video').canPlayType;

export function createVideoContainer(
  options: NormaledVideoOptions
): HTMLDivElement {
  const container = document.createElement('div');
  container.id = makeId('container');
  container.classList.add('ipywebcam');
  container.classList.add('video-container');
  const playbackAnimation = createPlaybackAnimation();
  container.appendChild(playbackAnimation);
  const video = document.createElement('video');
  video.id = makeId('video');
  video.classList.add('video');
  container.appendChild(video);
  const videoControls = createVideoControls(options);
  container.appendChild(videoControls);
  return container;
}

function iconShow(svg: SVGSVGElement, id: string): void {
  const uses = svg.getElementsByTagNameNS(svgNS, 'use');
  for (let i = 0; i < uses.length; ++i) {
    const use = uses[i] as SVGUseElement;
    if (use.classList.contains(`use-${id}`)) {
      use.classList.remove('hidden');
    } else {
      use.classList.add('hidden');
    }
  }
}

function isPipEnabled(): boolean {
  return !!(document as any).pictureInPictureEnabled;
}

export interface VideoShortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
}

type NormaledVideoShortcut = Required<VideoShortcut>;

function descShortcut(shortcut: NormaledVideoShortcut): string {
  const parts: string[] = [];
  if (shortcut.ctrl) {
    parts.push('ctrl');
  }
  if (shortcut.alt) {
    parts.push('alt');
  }
  if (shortcut.shift) {
    parts.push('shift');
  }
  parts.push(shortcut.key);
  return parts.join(' + ');
}

export interface VideoOptions {
  shortcuts?: {
    play?: string | VideoShortcut;
    mute?: string | VideoShortcut;
    fullscreen?: string | VideoShortcut;
    pip?: string | VideoShortcut;
  };
}

interface NormaledVideoOptions {
  shortcuts: {
    play: NormaledVideoShortcut;
    mute: NormaledVideoShortcut;
    fullscreen: NormaledVideoShortcut;
    pip: NormaledVideoShortcut;
  };
}

const DEFAULT_OPTIONS: VideoOptions = {
  shortcuts: {
    play: 'k',
    mute: 'm',
    fullscreen: 'f',
    pip: 'p',
  },
};

function makeShortcut(shortcut: string | VideoShortcut): NormaledVideoShortcut {
  if (typeof shortcut === 'string') {
    return {
      key: shortcut,
      ctrl: false,
      alt: false,
      shift: false,
    };
  } else {
    return {
      key: shortcut.key,
      ctrl: shortcut.ctrl || false,
      alt: shortcut.alt || false,
      shift: shortcut.shift || false,
    };
  }
}

function makeOptions(otps: VideoOptions): NormaledVideoOptions {
  const options = Object.assign({}, DEFAULT_OPTIONS, otps);
  options.shortcuts = Object.assign(
    {},
    DEFAULT_OPTIONS.shortcuts,
    otps.shortcuts
  );
  options.shortcuts.fullscreen = makeShortcut(options.shortcuts.fullscreen!);
  options.shortcuts.mute = makeShortcut(options.shortcuts.mute!);
  options.shortcuts.pip = makeShortcut(options.shortcuts.pip!);
  options.shortcuts.play = makeShortcut(options.shortcuts.play!);
  return options as NormaledVideoOptions;
}

export class Video {
  options: NormaledVideoOptions;
  container: HTMLDivElement;
  video: HTMLVideoElement;
  videoControls: HTMLDivElement;
  playButton: HTMLButtonElement;
  timeElapsed: HTMLTimeElement;
  duration: HTMLTimeElement;
  progress: HTMLProgressElement;
  seek: HTMLInputElement;
  seekTooltip: HTMLDivElement;
  volume: HTMLInputElement;
  volumeButton: HTMLButtonElement;
  volumeIcons: SVGSVGElement;
  playbackAnimation: HTMLDivElement;
  fullscreenButton: HTMLButtonElement;
  fullscreenIcons: SVGSVGElement;
  pipButton: HTMLButtonElement;

  constructor(opts: VideoOptions = {}) {
    this.options = makeOptions(opts);
    this.installSvg();
    this.container = createVideoContainer(this.options);
    this.video = this.container.querySelector(
      'video.video'
    )! as HTMLVideoElement;
    this.videoControls = this.container.querySelector(
      'div.video-controls'
    )! as HTMLDivElement;
    this.playButton = this.container.querySelector(
      'button.play'
    )! as HTMLButtonElement;
    this.timeElapsed = this.container.querySelector(
      'time.time-elapsed'
    )! as HTMLTimeElement;
    this.duration = this.container.querySelector(
      'time.duration'
    )! as HTMLTimeElement;
    this.progress = this.container.querySelector(
      'progress.progress-bar'
    )! as HTMLProgressElement;
    this.seek = this.container.querySelector('input.seek')! as HTMLInputElement;
    this.seekTooltip = this.container.querySelector(
      'div.seek-tooltip'
    )! as HTMLDivElement;
    this.volume = this.container.querySelector(
      'input.volume'
    )! as HTMLInputElement;
    this.volumeButton = this.container.querySelector(
      'button.volume-button'
    )! as HTMLButtonElement;
    this.volumeIcons = this.volumeButton.querySelector('svg')! as SVGSVGElement;
    this.playbackAnimation = this.container.querySelector(
      'div.playback-animation'
    )! as HTMLDivElement;
    this.fullscreenButton = this.container.querySelector(
      'button.fullscreen-button'
    )! as HTMLButtonElement;
    this.fullscreenIcons = this.fullscreenButton.querySelector(
      'svg'
    )! as SVGSVGElement;
    this.pipButton = this.container.querySelector(
      'button.pip-button'
    )! as HTMLButtonElement;
    this.playButton.addEventListener('click', this.togglePlay);
    this.video.addEventListener('play', this.updatePlayButton);
    this.video.addEventListener('pause', this.updatePlayButton);
    this.video.addEventListener('loadedmetadata', this.initializeVideo);
    this.video.addEventListener('timeupdate', this.updateTimeElapsed);
    this.video.addEventListener('timeupdate', this.updateProgress);
    this.video.addEventListener('volumechange', this.updateVolumeIcon);
    this.video.addEventListener('click', this.togglePlay);
    this.video.addEventListener('click', this.animatePlayback);
    this.video.addEventListener('mouseenter', this.showControls);
    this.video.addEventListener('mouseleave', this.hideControls);
    this.videoControls.addEventListener('mouseenter', this.showControls);
    this.videoControls.addEventListener('mouseleave', this.hideControls);
    this.seek.addEventListener('mousemove', this.updateSeekTooltip);
    this.seek.addEventListener('input', this.skipAhead);
    this.volume.addEventListener('input', this.updateVolume);
    this.volumeButton.addEventListener('click', this.toggleMute);
    this.fullscreenButton.addEventListener('click', this.toggleFullScreen);
    this.container.addEventListener(
      'fullscreenchange',
      this.updateFullscreenButton
    );
    this.pipButton.addEventListener('click', this.togglePip);
    document.addEventListener('keyup', this.keyboardShortcuts);
  }

  destroy = (): void => {
    document.removeEventListener('keyup', this.keyboardShortcuts);
    const url = this.video.src;
    this.video.src = '';
    if (url) {
      URL.revokeObjectURL(url);
    }
  };

  updateData = (blob: Blob | MediaSource): void => {
    const oldUrl = this.video.src;
    const url = URL.createObjectURL(blob);
    this.video.src = url;
    if (oldUrl) {
      URL.revokeObjectURL(this.video.src);
    }
  };

  installSvg = (): void => {
    const id = makeId('icons');
    const svg = document.getElementById(id);
    if (!svg) {
      document.body.appendChild(createControlsSvg());
    }
  };

  togglePlay = (): void => {
    if (this.video.paused || this.video.ended) {
      this.video.play();
    } else {
      this.video.pause();
    }
  };

  enableControls = (enabled: boolean): void => {
    if (enabled) {
      if (VIDEO_WORKS) {
        this.video.controls = false;
        this.videoControls.classList.remove('hidden');
      } else {
        this.video.controls = true;
        this.videoControls.classList.add('hidden');
      }
    } else {
      this.video.controls = false;
      this.videoControls.classList.add('hidden');
    }
  };

  updatePlayButton = (): void => {
    const svg = this.playButton.getElementsByClassName(
      'playback-icons'
    )[0] as SVGSVGElement;
    const shortcut = descShortcut(this.options.shortcuts.play);
    if (this.video.paused || this.video.ended) {
      iconShow(svg, 'play-icon');
      this.playButton.setAttribute('data-title', `Play (${shortcut})`);
    } else {
      iconShow(svg, 'pause');
      this.playButton.setAttribute('data-title', `Pause (${shortcut})`);
    }
  };

  initializeVideo = (): void => {
    const videoDuration = Math.round(this.video.duration);
    this.seek.setAttribute('max', `${videoDuration}`);
    this.progress.setAttribute('max', `${videoDuration}`);
    const time = formatTime(videoDuration);
    this.duration.innerText = `${time.minutes}:${time.seconds}`;
    this.duration.setAttribute('datetime', `${time.minutes}m ${time.seconds}s`);
  };

  // updateTimeElapsed indicates how far through the video
  // the current playback is by updating the timeElapsed element
  updateTimeElapsed = (): void => {
    const time = formatTime(Math.round(this.video.currentTime));
    this.timeElapsed.innerText = `${time.minutes}:${time.seconds}`;
    this.timeElapsed.setAttribute(
      'datetime',
      `${time.minutes}m ${time.seconds}s`
    );
  };

  // updateProgress indicates how far through the video
  // the current playback is by updating the progress bar
  updateProgress = (): void => {
    this.seek.value = `${Math.floor(this.video.currentTime)}`;
    this.progress.value = Math.floor(this.video.currentTime);
  };

  // updateSeekTooltip uses the position of the mouse on the progress bar to
  // roughly work out what point in the video the user will skip to if
  // the progress bar is clicked at that point
  updateSeekTooltip = (event: MouseEvent): void => {
    const skipTo = Math.round(
      (event.offsetX / this.seek.clientWidth) *
        parseInt(this.seek.getAttribute('max') || '0', 10)
    );
    this.seek.setAttribute('data-seek', `${skipTo}`);
    const t = formatTime(skipTo);
    this.seekTooltip.textContent = `${t.minutes}:${t.seconds}`;
    const rect = this.video.getBoundingClientRect();
    this.seekTooltip.style.left = `${event.pageX - rect.left}px`;
  };

  // skipAhead jumps to a different point in the video when the progress bar
  // is clicked
  skipAhead = (): void => {
    const skipTo = this.seek.dataset.seek
      ? this.seek.dataset.seek
      : this.seek.value;
    this.video.currentTime = Number.parseFloat(skipTo);
    this.progress.value = Number.parseFloat(skipTo);
    this.seek.value = skipTo;
  };

  // updateVolume updates the video's volume
  // and disables the muted state if active
  updateVolume = (): void => {
    if (this.video.muted) {
      this.video.muted = false;
    }
    this.video.volume = Number.parseFloat(this.volume.value);
  };

  // updateVolumeIcon updates the volume icon so that it correctly reflects
  // the volume of the video
  updateVolumeIcon = (): void => {
    const shortcut = descShortcut(this.options.shortcuts.mute);
    this.volumeButton.setAttribute('data-title', `Mute (${shortcut})`);
    if (this.video.muted || this.video.volume === 0) {
      this.volumeButton.setAttribute('data-title', `Unmute (${shortcut})`);
      iconShow(this.volumeIcons, 'volume-mute');
    } else if (this.video.volume > 0 && this.video.volume <= 0.5) {
      iconShow(this.volumeIcons, 'volume-low');
    } else {
      iconShow(this.volumeIcons, 'volume-high');
    }
  };

  // toggleMute mutes or unmutes the video when executed
  // When the video is unmuted, the volume is returned to the value
  // it was set to before the video was muted
  toggleMute = (): void => {
    this.video.muted = !this.video.muted;

    if (this.video.muted) {
      this.volume.setAttribute('data-volume', this.volume.value);
      this.volume.value = '0';
    } else {
      this.volume.value = this.volume.dataset.volume || `${this.video.volume}`;
    }
  };

  // animatePlayback displays an animation when
  // the video is played or paused
  animatePlayback = (): void => {
    this.playbackAnimation.animate(
      [
        {
          opacity: 1,
          transform: 'scale(1)',
        },
        {
          opacity: 0,
          transform: 'scale(1.3)',
        },
      ],
      {
        duration: 500,
      }
    );
  };

  // toggleFullScreen toggles the full screen state of the video
  // If the browser is currently in fullscreen mode,
  // then it should exit and vice versa.
  toggleFullScreen = (): void => {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else if ((document as any).webkitFullscreenElement) {
      // Need this to support Safari
      (document as any).webkitExitFullscreen();
    } else if ((this.container as any).webkitRequestFullscreen) {
      // Need this to support Safari
      (this.container as any).webkitRequestFullscreen();
    } else {
      this.container.requestFullscreen();
    }
  };

  isFullscreen = (): boolean => {
    return (
      document.fullscreenElement ||
      (document as any).webkitFullscreenElement ||
      (this.container as any).webkitRequestFullscreen
    );
  };

  // updateFullscreenButton changes the icon of the full screen button
  // and tooltip to reflect the current full screen state of the video
  updateFullscreenButton = (): void => {
    const shortcut = descShortcut(this.options.shortcuts.fullscreen);
    if (this.isFullscreen()) {
      this.fullscreenButton.setAttribute(
        'data-title',
        `Exit full screen (${shortcut})`
      );
      iconShow(this.fullscreenIcons, 'fullscreen-exit');
    } else {
      this.fullscreenButton.setAttribute(
        'data-title',
        `Full screen (${shortcut})`
      );
      iconShow(this.fullscreenIcons, 'fullscreen');
    }
  };

  // togglePip toggles Picture-in-Picture mode on the video
  togglePip = async (): Promise<void> => {
    try {
      if (this.video !== (document as any).pictureInPictureElement) {
        this.pipButton.disabled = true;
        await (this.video as any).requestPictureInPicture();
      } else {
        await (document as any).exitPictureInPicture();
      }
    } catch (error) {
      console.error(error);
    } finally {
      this.pipButton.disabled = false;
    }
  };

  // hideControls hides the video controls when not in use
  // if the video is paused, the controls must remain visible
  hideControls = (): void => {
    if (this.video.paused) {
      return;
    }

    this.videoControls.classList.add('hide');
  };

  // showControls displays the video controls
  showControls = (): void => {
    this.videoControls.classList.remove('hide');
  };

  // keyboardShortcuts executes the relevant functions for
  // each supported shortcut key
  keyboardShortcuts = (event: KeyboardEvent): void => {
    const { key, ctrlKey, altKey, shiftKey } = event;
    const { play, mute, fullscreen, pip } = this.options.shortcuts;
    if (
      key === play.key &&
      (play.ctrl === !!ctrlKey ||
        play.alt === !!altKey ||
        play.shift === !!shiftKey)
    ) {
      this.togglePlay();
      this.animatePlayback();
      if (this.video.paused) {
        this.showControls();
      } else {
        setTimeout(() => {
          this.hideControls();
        }, 2000);
      }
    } else if (
      key === mute.key &&
      (mute.ctrl === !!ctrlKey ||
        mute.alt === !!altKey ||
        mute.shift === !!shiftKey)
    ) {
      this.toggleMute();
    } else if (
      key === fullscreen.key &&
      (fullscreen.ctrl === !!ctrlKey ||
        fullscreen.alt === !!altKey ||
        fullscreen.shift === !!shiftKey)
    ) {
      this.toggleFullScreen();
    } else if (
      key === pip.key &&
      (pip.ctrl === !!ctrlKey ||
        pip.alt === !!altKey ||
        pip.shift === !!shiftKey)
    ) {
      this.togglePip();
    }
  };
}

// formatTime takes a time length in seconds and returns the time in
// minutes and seconds
function formatTime(timeInSeconds: number) {
  const result = new Date(timeInSeconds * 1000).toISOString().substr(11, 8);

  return {
    minutes: result.substr(3, 2),
    seconds: result.substr(6, 2),
  };
}
