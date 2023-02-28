/* eslint-disable @typescript-eslint/no-non-null-assertion */

import '../css/video.css';
import { makeLineChart } from './charts';
import { RangeBar } from './range';
import { arrayInclude, arrayRemove } from './utils';
import { RecorderMeta } from './types';

const svgNS = 'http://www.w3.org/2000/svg';
const prefix = 'ipywebcam-video-';
export function makeId(id: string): string {
  return `${prefix}${id}`;
}

function createSymbol(
  id: string,
  pathD: string | string[],
  viewBox = '0 0 24 24',
  gTrans = ''
): SVGSymbolElement {
  const symbol = document.createElementNS(svgNS, 'symbol');
  symbol.id = makeId(id);
  symbol.setAttribute('viewBox', viewBox);
  if (Array.isArray(pathD)) {
    const group = document.createElementNS(svgNS, 'g');
    if (gTrans) {
      group.setAttribute('transform', gTrans);
    }
    for (const p of pathD) {
      const path = document.createElementNS(svgNS, 'path');
      path.setAttribute('d', p);
      group.appendChild(path);
    }
    symbol.appendChild(group);
  } else {
    const path = document.createElementNS(svgNS, 'path');
    path.setAttribute('d', pathD);
    symbol.appendChild(path);
  }
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
  defs.appendChild(
    createSymbol(
      'left-arrow',
      'M15.293 3.293 6.586 12l8.707 8.707 1.414-1.414L9.414 12l7.293-7.293-1.414-1.414z'
    )
  );
  defs.appendChild(
    createSymbol(
      'right-arrow',
      'M7.293 4.707 14.586 12l-7.293 7.293 1.414 1.414L17.414 12 8.707 3.293 7.293 4.707z'
    )
  );
  defs.appendChild(
    createSymbol(
      'statistics',
      [
        'M2096 2741 c-15 -10 -37 -32 -47 -47 -18 -28 -19 -65 -19 -984 l0 -955 25 -37 c32 -48 47 -50 268 -46 l179 3 29 33 29 32 0 969 c0 967 0 968 -21 995 -40 50 -64 56 -246 56 -148 0 -171 -2 -197 -19z',
        'M1308 2088 c-30 -8 -41 -18 -58 -52 -19 -41 -20 -58 -20 -643 0 -330 3 -613 6 -629 3 -16 16 -42 30 -59 l24 -30 210 0 210 0 24 30 c14 17 27 43 30 59 3 16 6 299 6 629 0 584 -1 602 -20 643 -18 36 -27 43 -65 53 -53 13 -326 13 -377 -1z',
        'M504 1426 c-64 -28 -64 -28 -64 -373 l0 -313 29 -32 29 -33 179 -3 c221 -4 236 -2 268 46 l25 37 0 293 c0 328 -3 347 -65 376 -44 21 -353 22 -401 2z',
        'M42 468 c-39 -32 -41 -35 -41 -91 -1 -42 3 -59 14 -63 8 -3 17 -13 20 -23 3 -9 18 -24 34 -34 27 -16 124 -17 1431 -17 1307 0 1404 1 1431 17 16 10 31 25 34 34 3 10 12 20 20 23 11 4 15 21 15 58 0 49 -3 56 -40 91 l-40 37 -1419 0 -1419 0 -40 -32z',
      ],
      '0 0 1000 1000',
      'translate(100, 900) scale(0.25, -0.25)'
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

function createVideoProgress(): HTMLDivElement {
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
  const rangeBar = document.createElement('div');
  rangeBar.setAttribute('draggable', 'false');
  rangeBar.classList.add('range-bar', 'hidden');
  const tooltip = document.createElement('div');
  tooltip.id = makeId('seek-tooltip');
  tooltip.classList.add('seek-tooltip');
  tooltip.innerText = '00:00';
  container.appendChild(progress);
  container.appendChild(input);
  container.appendChild(tooltip);
  container.appendChild(rangeBar);
  return container;
}

function createStatisticsContainer(): HTMLDivElement {
  const container = document.createElement('div');
  container.classList.add('statistics-container', 'hidden', 'unused');
  const svg = document.createElementNS(svgNS, 'svg');
  container.appendChild(svg);
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
  const span = document.createElement('span');
  span.innerText = ' / ';
  container.appendChild(span);
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

function createIndexSelector(): HTMLButtonElement {
  const container = document.createElement('button');
  container.id = makeId('index-selector');
  container.classList.add('index-selector');
  container.classList.add('text-button');
  container.classList.add('hidden');
  container.setAttribute('data-title', 'Select Index');
  const text = document.createElement('div');
  text.classList.add('text');
  container.appendChild(text);
  return container;
}

function createSpeedSelector(): HTMLButtonElement {
  const container = document.createElement('button');
  container.id = makeId('speed-selector');
  container.classList.add('speed-selector');
  container.classList.add('text-button');
  container.setAttribute('data-title', 'Select Speed');
  const text = document.createElement('div');
  text.classList.add('text');
  container.appendChild(text);
  return container;
}

function createChannelSelector(): HTMLButtonElement {
  const container = document.createElement('button');
  container.id = makeId('channel-selector');
  container.classList.add('channel-selector');
  container.classList.add('text-button');
  container.classList.add('hidden');
  container.setAttribute('data-title', 'Select Channel');
  const text = document.createElement('div');
  text.classList.add('text');
  container.appendChild(text);
  return container;
}

function createStatsSelector(): HTMLButtonElement {
  const container = document.createElement('button');
  container.classList.add('stats-selector', 'hidden');
  container.setAttribute('data-title', 'Select Statistics Type');
  const icon = createSelectiveUses('statistics', 'statistics');
  icon.classList.add('icon');
  container.appendChild(icon);
  const text = document.createElement('div');
  text.classList.add('text');
  container.appendChild(text);
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
  const statsSelector = createStatsSelector();
  container.appendChild(statsSelector);
  const indexSelector = createIndexSelector();
  container.appendChild(indexSelector);
  const channelSelector = createChannelSelector();
  container.appendChild(channelSelector);
  const speedSelector = createSpeedSelector();
  container.appendChild(speedSelector);
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
  container.setAttribute('draggable', 'false');
  container.classList.add('video-controls');
  container.tabIndex = 0;
  const videoProgress = createVideoProgress();
  container.appendChild(videoProgress);
  const statistics = createStatisticsContainer();
  container.appendChild(statistics);
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

type IndexSelectHandler = (index: number) => void;
type ChannelSelectHandler = (channel: string) => void;

interface Option<V = any> {
  label: string;
  value: V;
}

type OptionSelectHandler<V> = (option: Option<V>) => void;

class SelectorPannel<V = any> {
  trigger: Element | undefined;
  container: HTMLDivElement;
  options: Array<Option<V>> = [];
  optionButtons: HTMLButtonElement[] = [];
  clickHandlers: Array<OptionSelectHandler<V>> = [];
  realClickHandlers: Array<(evt: MouseEvent) => any> = [];

  constructor(options: Array<Option<V>>) {
    this.container = document.createElement('div');
    this.container.classList.add('selector-panel');
    this.container.classList.add('selector-options');
    this.container.tabIndex = -1;
    this.container.addEventListener('focusout', (evt) => {
      if (
        !this.container.contains(evt.relatedTarget as Element) &&
        evt.relatedTarget !== this.trigger
      ) {
        this.hidden();
      }
    });
    this.updateView(options);
  }

  layout = () => {
    const { width, height } = this.container.getBoundingClientRect();
    this.container.style.left = `-${width / 2}px`;
    this.container.style.top = `-${height}px`;
  };

  show = () => {
    this.container.classList.remove('hidden');
    this.layout();
    this.container.focus();
  };

  hidden = () => {
    this.container.classList.add('hidden');
  };

  toggle = () => {
    if (this.container.classList.contains('hidden')) {
      this.show();
    } else {
      this.hidden();
    }
  };

  findOption = (options: Array<Option<V>>, label: string): number => {
    for (let i = 0; i < options.length; ++i) {
      const option = options[i];
      if (option.label === label) {
        return i;
      }
    }
    return -1;
  };

  updateViewAfterSelect = (label: string): void => {
    const index = this.findOption(this.options, label);
    if (index === -1) {
      return;
    }
    this.container.querySelectorAll('button.selector-option').forEach((e) => {
      e.classList.remove('selected');
    });
    const option = this.container.querySelector(
      `button.selector-option-${index}`
    );
    if (option) {
      option.classList.add('selected');
    }
  };

  select = (label: string): void => {
    const index = this.findOption(this.options, label);
    if (index !== -1) {
      const option = this.options[index];
      (this.clickHandlers || []).forEach((handler) => {
        handler(option);
      });
      this.updateViewAfterSelect(option.label);
    }
  };

  install = (
    element: Element,
    handler: OptionSelectHandler<V>,
    initLabel: string | undefined = undefined
  ): SelectorPannel<V> => {
    this.trigger = element;
    this.hidden();
    this.addClickHandler(handler);
    element.appendChild(this.container);
    element.addEventListener('click', () => {
      this.toggle();
    });
    if (initLabel) {
      this.select(initLabel);
    }
    return this;
  };

  addClickHandler = (handler: OptionSelectHandler<V>): void => {
    this.clickHandlers.push(handler);
  };

  createHandler = (option: Option<V>): ((evt: MouseEvent) => any) => {
    return (evt: MouseEvent) => {
      evt.stopPropagation();
      try {
        this.select(option.label);
        this.hidden();
      } catch (e) {
        console.error(e);
      }
    };
  };

  updateView = (options: Array<Option<V>>): void => {
    const buttons = this.optionButtons;
    const handlers = this.realClickHandlers;
    const newLen = options.length;
    const oldLen = buttons.length;
    for (let i = 0; i < oldLen; ++i) {
      const button = buttons[i];
      const handler = handlers[i];
      if (i < newLen) {
        const option = options[i];
        button.innerText = option.label;
        button.removeEventListener('click', handler);
        const newHandler = this.createHandler(option);
        button.addEventListener('click', newHandler);
        handlers[i] = newHandler;
      } else {
        button.removeEventListener('click', handler);
        this.container.removeChild(button);
      }
    }
    if (oldLen > newLen) {
      buttons.splice(newLen, oldLen - newLen);
      handlers.splice(newLen, oldLen - newLen);
    }
    if (oldLen < newLen) {
      for (let i = oldLen; i < newLen; ++i) {
        const option = options[i];
        const button = document.createElement('button');
        button.innerText = option.label;
        button.classList.add('selector-option');
        button.classList.add('no-tooltip');
        button.classList.add(`selector-option-${i}`);
        button.setAttribute('data-index', `${i}`);
        const handler = this.createHandler(option);
        button.addEventListener('click', handler);
        this.container.appendChild(button);
        buttons.push(button);
        handlers.push(handler);
      }
    }
    this.options = options;
  };
}

class IndexSelectorPannel {
  trigger: Element | undefined;
  container: HTMLDivElement;
  options: HTMLDivElement;
  pager: HTMLDivElement | undefined;
  pagerLeft: HTMLButtonElement | undefined;
  pagerNumber: HTMLDivElement | undefined;
  pagerRight: HTMLButtonElement | undefined;
  size: number;
  // 1-start
  pageIndex: number;
  pageSize: number;
  selected: number;
  row: number;
  column: number;
  hasPager: boolean;
  optionsWidth: number;
  optionsHeight: number;
  clickHandlers: IndexSelectHandler[] = [];
  realClickHandlers: Array<(evt: MouseEvent) => any> = [];

  constructor(size: number) {
    this.container = document.createElement('div');
    this.container.id = makeId('selector-panel');
    this.container.classList.add('selector-panel');
    this.container.tabIndex = -1;
    this.options = document.createElement('div');
    this.options.classList.add('selector-options');
    this.options.classList.add('grid');
    this.container.appendChild(this.options);
    this.container.addEventListener('focusout', (evt) => {
      if (
        !this.container.contains(evt.relatedTarget as Element) &&
        evt.relatedTarget !== this.trigger
      ) {
        this.hidden();
      }
    });
    this.updateSize(size);
  }

  calcLayout = (pageIndex: number) => {
    this.row = Math.ceil(this.size / 4);
    this.column = Math.min(this.size, 4);
    this.hasPager = this.row > 6;
    this.pageIndex = pageIndex;
    this.pageSize = Math.ceil(this.size / 24);
    const curRow =
      this.pageIndex < this.pageSize ? 6 : this.row - (this.pageIndex - 1) * 6;
    this.optionsWidth = this.column * 32 + (this.column - 1) * 6 + 6;
    this.optionsHeight = curRow * 32 + (curRow - 1) * 6 + 6;
    const height = this.optionsHeight + (this.hasPager ? 32 : 0);
    this.container.style.width = `${this.optionsWidth}px`;
    this.container.style.height = `${height}px`;
    this.container.style.left = `${-this.optionsWidth / 2}px`;
    this.container.style.top = `${-height}px`;
  };

  show = () => {
    this.container.classList.remove('hidden');
    this.container.focus();
  };

  hidden = () => {
    this.container.classList.add('hidden');
  };

  toggle = () => {
    if (this.container.classList.contains('hidden')) {
      this.show();
    } else {
      this.hidden();
    }
  };

  addClickHandler = (handler: IndexSelectHandler): void => {
    this.clickHandlers.push(handler);
  };

  calcPageIndexFromIndex = (index: number): number => {
    if (index < 0 || index >= this.size) {
      throw new Error(`Invalid index ${index}`);
    }
    return Math.ceil((index + 1) / 24);
  };

  setSelectIndex = (index: number): void => {
    this.updatePage(this.calcPageIndexFromIndex(index));
    this.selected = index;
    this.container.querySelectorAll('button.selector-option').forEach((e) => {
      e.classList.remove('selected');
    });
    const option = this.container.querySelector(
      `button.selector-option-${index}`
    );
    if (option) {
      option.classList.add('selected');
    }
  };

  createHandler = (index: number): ((evt: MouseEvent) => any) => {
    return (evt: MouseEvent) => {
      evt.stopPropagation();
      try {
        (this.clickHandlers || []).forEach((handler) => {
          handler(index);
        });
        this.hidden();
      } catch (e) {
        console.error(e);
      }
    };
  };

  updatePage = (pageIndex: number) => {
    if (pageIndex !== this.pageIndex) {
      this.calcLayout(pageIndex);
      const optNum = this.pageIndex < this.pageSize ? 24 : this.size % 24;
      let len = this.options.children.length;
      let idx = 0;
      for (let i = 0; i < len; ++i) {
        const child = this.options.children.item(i);
        if (child?.classList.contains('selector-option')) {
          const button = child as HTMLButtonElement;
          const oldHandler = this.realClickHandlers[idx];
          const dataIdx = idx + (pageIndex - 1) * 24;
          if (idx < optNum) {
            const newHandler = (this.realClickHandlers[idx] =
              this.createHandler(dataIdx));
            button.removeEventListener('click', oldHandler);
            button.addEventListener('click', newHandler);
            button.innerText = `${dataIdx}`;
            button.className = '';
            button.classList.add('selector-option');
            button.classList.add('no-tooltip');
            button.classList.add(`selector-option-${dataIdx}`);
            if (dataIdx === this.selected) {
              button.classList.add('selected');
            } else {
              button.classList.remove('selected');
            }
            ++idx;
          } else {
            button.removeEventListener('click', oldHandler);
            this.options.removeChild(button);
            --i;
            --len;
          }
        }
      }
      if (this.realClickHandlers.length > optNum) {
        this.realClickHandlers.splice(
          optNum,
          this.realClickHandlers.length - optNum
        );
      }
      if (idx < optNum) {
        for (let i = idx; i < optNum; ++i) {
          const dataIdx = i + (pageIndex - 1) * 24;
          const option = document.createElement('button');
          option.innerText = `${dataIdx}`;
          option.classList.add('selector-option');
          option.classList.add('no-tooltip');
          option.classList.add(`selector-option-${dataIdx}`);
          if (dataIdx === this.selected) {
            option.classList.add('selected');
          } else {
            option.classList.remove('selected');
          }
          option.setAttribute('data-index', `${dataIdx}`);
          const handler = this.createHandler(dataIdx);
          this.realClickHandlers.push(handler);
          option.addEventListener('click', handler);
          this.options.appendChild(option);
        }
      }
      if (this.hasPager) {
        if (this.pager) {
          if (this.pagerLeft && this.pageIndex <= 1) {
            this.pagerLeft.classList.add('disabled');
          } else if (this.pagerLeft) {
            this.pagerLeft.classList.remove('disabled');
          }
          if (this.pagerNumber) {
            this.pagerNumber.innerText = `${pageIndex} / ${this.pageSize}`;
          }
          if (this.pagerRight && this.pageIndex >= this.pageSize) {
            this.pagerRight.classList.add('disabled');
          } else if (this.pagerRight) {
            this.pagerRight.classList.remove('disabled');
          }
        } else {
          this.pager = document.createElement('div');
          this.pager.classList.add('selector-pager');
          this.pagerLeft = document.createElement('button');
          this.pagerLeft.classList.add('page-left');
          this.pagerLeft.classList.add('no-tooltip');
          this.pagerLeft.tabIndex = -1;
          this.pagerLeft.appendChild(
            createSelectiveUses('left-arrow', 'left-arrow')
          );
          if (this.pageIndex <= 1) {
            this.pagerLeft.classList.add('disabled');
          }
          this.pagerLeft.addEventListener('click', (evt) => {
            evt.stopPropagation();
            if (this.pageIndex > 1) {
              this.updatePage(this.pageIndex - 1);
            }
          });
          this.pager.appendChild(this.pagerLeft);
          this.pagerNumber = document.createElement('div');
          this.pagerNumber.innerText = `${pageIndex} / ${this.pageSize}`;
          this.pager.appendChild(this.pagerNumber);
          this.pagerRight = document.createElement('button');
          this.pagerRight.classList.add('page-right');
          this.pagerRight.classList.add('no-tooltip');
          this.pagerRight.tabIndex = -1;
          this.pagerRight.appendChild(
            createSelectiveUses('right-arrow', 'right-arrow')
          );
          if (this.pageIndex >= this.pageSize) {
            this.pagerRight.classList.add('disabled');
          }
          this.pagerRight.addEventListener('click', (evt) => {
            evt.stopPropagation();
            if (this.pageIndex < this.pageSize) {
              this.updatePage(this.pageIndex + 1);
            }
          });
          this.pager.appendChild(this.pagerRight);
          this.container.appendChild(this.pager);
        }
      } else {
        if (this.pager) {
          this.container.removeChild(this.pager);
          this.pager = undefined;
          this.pagerNumber = undefined;
        }
      }
    }
  };

  updateSize = (size: number) => {
    if (this.size !== size) {
      this.size = size;
      this.pageIndex = 0;
      this.updatePage(1);
    }
  };
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
    range?: string | VideoShortcut;
    stats?: string | VideoShortcut;
  };
}

interface NormaledVideoOptions {
  shortcuts: {
    play: NormaledVideoShortcut;
    mute: NormaledVideoShortcut;
    fullscreen: NormaledVideoShortcut;
    pip: NormaledVideoShortcut;
    range: NormaledVideoShortcut;
    stats: NormaledVideoShortcut;
  };
}

const DEFAULT_OPTIONS: VideoOptions = {
  shortcuts: {
    play: 'k',
    mute: 'm',
    fullscreen: 'f',
    pip: 'p',
    range: 'v',
    stats: 's',
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
  options.shortcuts.range = makeShortcut(options.shortcuts.range!);
  options.shortcuts.stats = makeShortcut(options.shortcuts.stats!);
  return options as NormaledVideoOptions;
}

const SpeedOptions: Array<Option<number>> = [
  { label: '0.25x', value: 0.25 },
  { label: '0.5x', value: 0.5 },
  { label: '0.75x', value: 0.75 },
  { label: '1.0x', value: 1 },
  { label: '1.25x', value: 1.25 },
  { label: '1.5x', value: 1.5 },
  { label: '1.75x', value: 1.75 },
  { label: '2.0x', value: 2 },
  { label: '2.5x', value: 2.5 },
  { label: '3.0x', value: 3 },
];

type VideoInitHandler = (video: Video) => void;

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
  rangeBar: RangeBar;
  statisticsBar: HTMLDivElement;
  statisticsSvg: SVGSVGElement;
  volume: HTMLInputElement;
  volumeButton: HTMLButtonElement;
  volumeIcons: SVGSVGElement;
  playbackAnimation: HTMLDivElement;
  fullscreenButton: HTMLButtonElement;
  fullscreenIcons: SVGSVGElement;
  pipButton: HTMLButtonElement;
  indexSelector: HTMLButtonElement;
  indexSelectorPannel: IndexSelectorPannel | undefined;
  indexSelectHandlers: IndexSelectHandler[] = [];
  indexerIndex = -1;
  indexerSize = 0;
  statsSelector: HTMLButtonElement;
  statsSelectorPannel: SelectorPannel<string>;
  stats = '';
  statsData: Required<RecorderMeta>['statistics'] = {};
  statsMeta: Required<RecorderMeta>['statistics_meta'] = {};
  speedSelector: HTMLButtonElement;
  speedSelectorPannel: SelectorPannel<number>;
  speed = 1;
  channelSelector: HTMLButtonElement;
  channelSelectHandlers: ChannelSelectHandler[] = [];
  channelSelectorPannel: SelectorPannel<string>;
  channel = '';
  currentTime: number | undefined;
  videoInitHandlers: VideoInitHandler[] = [];

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
    this.rangeBar = new RangeBar(
      this.container.querySelector('div.range-bar')! as HTMLDivElement
    );
    this.statisticsBar = this.container.querySelector(
      'div.statistics-container'
    )! as HTMLDivElement;
    this.statisticsSvg = this.statisticsBar.querySelector(
      'svg'
    )! as SVGSVGElement;
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
    this.indexSelector = this.container.querySelector(
      'button.index-selector'
    )! as HTMLButtonElement;
    this.statsSelector = this.container.querySelector(
      'button.stats-selector'
    )! as HTMLButtonElement;
    this.statsSelectorPannel = new SelectorPannel<string>([]).install(
      this.statsSelector,
      (option) => {
        const text = this.statsSelector.querySelector(
          'div.text'
        )! as HTMLDivElement;
        text.innerText = option.label;
        this.stats = option.value;
        if (this.video.duration > 0) {
          makeLineChart(
            this.statisticsSvg,
            this.statsData[this.stats],
            [0, this.video.duration],
            this.statsMeta[this.stats]?.y_range,
            this.video.clientWidth - 20,
            30
          );
        }
      }
    );
    this.speedSelector = this.container.querySelector(
      'button.speed-selector'
    )! as HTMLButtonElement;
    this.speedSelectorPannel = new SelectorPannel(SpeedOptions).install(
      this.speedSelector,
      (option: Option<number>): void => {
        const text = this.speedSelector.querySelector(
          'div.text'
        )! as HTMLDivElement;
        text.innerText = option.label;
        this.video.playbackRate = option.value;
        this.speed = option.value;
      },
      '1.0x'
    );
    this.channelSelector = this.container.querySelector(
      'button.channel-selector'
    )! as HTMLButtonElement;
    this.channelSelectorPannel = new SelectorPannel<string>([]).install(
      this.channelSelector,
      (option) => {
        const text = this.channelSelector.querySelector(
          'div.text'
        )! as HTMLDivElement;
        text.innerText = option.label;
        this.channelSelectHandlers.forEach((handler) => {
          handler(option.value);
        });
        this.channel = option.value;
      }
    );
    this.playButton.addEventListener('click', this.togglePlay);
    this.video.addEventListener('play', this.updateCurrentTime);
    this.video.addEventListener('play', this.updatePlayButton);
    this.video.addEventListener('play', () => {
      this.video.playbackRate = this.speed;
    });
    this.video.addEventListener('pause', this.updatePlayButton);
    this.video.addEventListener('loadedmetadata', this.initializeVideo);
    this.video.addEventListener('timeupdate', this.updateCurrentTime);
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
    this.rangeBar.destroy();
  };

  addVideoInitHandler = (handler: VideoInitHandler): void => {
    this.videoInitHandlers.push(handler);
  };

  removeVideoInitHandler = (handler: VideoInitHandler): void => {
    arrayRemove(this.videoInitHandlers, handler);
  };

  updateStatistics = (
    statistics: RecorderMeta['statistics'] = {},
    statistics_meta: RecorderMeta['statistics_meta'] = {}
  ): void => {
    this.statsData = statistics;
    this.statsMeta = statistics_meta;
    const keys = Object.keys(statistics);
    if (keys.length > 0) {
      this.statsSelector.classList.remove('hidden');
      this.statsSelectorPannel.updateView(
        keys.map((key) => ({ label: key, value: key }))
      );
      this.statisticsBar.classList.remove('unused');
      if (!arrayInclude(keys, this.stats)) {
        this.statsSelectorPannel.select(keys[0]);
      }
    } else {
      this.statsSelector.classList.add('hidden');
      this.statsSelectorPannel.updateView([]);
      this.statisticsBar.classList.add('unused');
    }
  };

  updateChannels = (channels: string[] = []): void => {
    if (channels.length > 0) {
      this.channelSelector.classList.remove('hidden');
      const options: Array<Option<string>> = [{ label: 'Default', value: '' }];
      channels.forEach((channel) => {
        options.push({ label: channel, value: channel });
      });
      this.channelSelectorPannel.updateView(options);
      if (!arrayInclude(channels, this.channel)) {
        this.channelSelectorPannel.select('Default');
      }
    } else {
      this.channelSelector.classList.add('hidden');
      this.channelSelectorPannel.updateView([]);
    }
  };

  addChannelSelectHandler = (handler: ChannelSelectHandler): void => {
    this.channelSelectHandlers.push(handler);
  };

  updateIndexerSize = (size: number): void => {
    if (!this.indexSelectorPannel) {
      if (size > 0) {
        this.indexSelectorPannel = new IndexSelectorPannel(size);
        this.indexSelectorPannel.hidden();
        this.indexSelectHandlers.forEach((handler) => {
          this.indexSelectorPannel?.addClickHandler(handler);
        });
        this.indexSelectorPannel.trigger = this.indexSelector;
        this.indexSelector.appendChild(this.indexSelectorPannel.container);
        this.indexSelector.addEventListener('click', () => {
          this.indexSelectorPannel?.toggle();
          const index = this.indexSelector.getAttribute('data-index');
          if (index) {
            this.indexSelectorPannel?.setSelectIndex(Number.parseInt(index));
          }
        });
        this.indexSelector.classList.remove('hidden');
      } else {
        this.indexSelector.classList.add('hidden');
      }
    } else {
      if (size <= 0) {
        this.indexSelectorPannel.hidden();
        this.indexSelector.classList.add('hidden');
      } else {
        this.indexSelectorPannel.updateSize(size);
        this.indexSelector.classList.remove('hidden');
      }
    }
    this.indexerSize = size;
  };

  updateIndexerIndex = (index: number): void => {
    const text = this.indexSelector.querySelector(
      'div.text'
    )! as HTMLDivElement;
    text.innerText = `${index}`;
    this.indexSelector.setAttribute('data-index', `${index}`);
    this.indexSelectorPannel?.setSelectIndex(index);
    this.indexerIndex = index;
  };

  addIndexSelectHandler = (handler: IndexSelectHandler): void => {
    this.indexSelectHandlers.push(handler);
    if (this.indexSelectorPannel) {
      this.indexSelectorPannel.addClickHandler(handler);
    }
  };

  updateData = (blob: Blob | MediaSource, resumeTime = false): void => {
    const oldUrl = this.video.src;
    const url = URL.createObjectURL(blob);
    this.video.src = url;
    if (oldUrl) {
      this.video.load();
      if (resumeTime && this.currentTime) {
        this.video.currentTime = this.currentTime;
      }
      URL.revokeObjectURL(oldUrl);
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
    const videoDuration = Math.floor(this.video.duration);
    this.seek.setAttribute('max', `${videoDuration}`);
    this.progress.setAttribute('max', `${videoDuration}`);
    const time = formatTime(videoDuration);
    this.duration.innerText = `${time.minutes}:${time.seconds}`;
    this.duration.setAttribute('datetime', `${time.minutes}m ${time.seconds}s`);
    this.rangeBar.max = videoDuration;
    for (const handler of this.videoInitHandlers) {
      handler(this);
    }
    if (this.stats) {
      this.statsSelectorPannel.select(this.stats);
    }
  };

  updateCurrentTime = (): void => {
    this.currentTime = this.video.currentTime;
  };

  // updateTimeElapsed indicates how far through the video
  // the current playback is by updating the timeElapsed element
  updateTimeElapsed = (): void => {
    const time = formatTime(Math.floor(this.video.currentTime));
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

  toggleRangeBar = (): void => {
    this.rangeBar.toggle();
  };

  toggleStatisticsBar = (): void => {
    this.statisticsBar.classList.toggle('hidden');
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

  isInFocus = (): boolean => {
    return document.activeElement?.contains(this.container) || false;
  };

  // keyboardShortcuts executes the relevant functions for
  // each supported shortcut key
  keyboardShortcuts = (event: KeyboardEvent): void => {
    if (!this.isInFocus()) {
      return;
    }
    const { key, ctrlKey, altKey, shiftKey } = event;
    const { play, mute, fullscreen, pip, range, stats } =
      this.options.shortcuts;
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
    } else if (
      key === range.key &&
      (range.ctrl === !!ctrlKey ||
        range.alt === !!altKey ||
        range.shift === !!shiftKey)
    ) {
      this.toggleRangeBar();
    } else if (
      key === stats.key &&
      (stats.ctrl === !!ctrlKey ||
        stats.alt === !!altKey ||
        stats.shift === !!shiftKey)
    ) {
      this.toggleStatisticsBar();
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
