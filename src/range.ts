/* eslint-disable @typescript-eslint/no-non-null-assertion */
import { arrayEqual, arrayRemove, calcMouseOffsetX } from './utils';

export interface RangeBarOption {
  max?: number;
  min?: number;
  step?: number;
}

export type OnRangeSelect = (
  range: [number, number],
  rangeBar: RangeBar
) => any;

export type OnMarkersChange = (markers: number[], rangeBar: RangeBar) => any;

export class RangeBar {
  container: HTMLDivElement;
  min: number;
  max: number;
  step: number;

  markers: { [key: number]: HTMLDivElement };
  floatingMarker?: HTMLDivElement;
  selectedKey?: number;
  rangeMasker: HTMLDivElement;
  selectedRange: [number, number] = [0, 0];
  markersChangeCallbacks: OnMarkersChange[] = [];
  rangeSelectedCallbacks: OnRangeSelect[] = [];

  constructor(container: HTMLDivElement, option: RangeBarOption = {}) {
    this.container = container;
    this.rangeMasker = document.createElement('div');
    this.rangeMasker.classList.add('range-mask', 'hidden');
    this.rangeMasker.addEventListener('click', (evt) => {
      evt.stopPropagation();
      this.unselectRange();
    });
    this.container.appendChild(this.rangeMasker);
    this.container.addEventListener('click', (evt) => {
      if (evt.ctrlKey) {
        const pos = this.adjustPos(evt.offsetX);
        this.addMarker(pos);
      } else {
        this.onMouseRangeSelect(evt);
      }
    });
    this.container.addEventListener('mouseover', (evt) => {
      const offsetX = calcMouseOffsetX(evt, this.container);
      if (evt.ctrlKey) {
        this.makeFloatingMarker(offsetX);
      } else {
        this.releaseFloatingMarker();
      }
    });
    this.container.addEventListener('mousemove', (evt) => {
      const offsetX = calcMouseOffsetX(evt, this.container);
      if (evt.ctrlKey) {
        this.makeFloatingMarker(offsetX);
      } else {
        this.releaseFloatingMarker();
      }
    });
    this.container.addEventListener('mouseout', () => {
      this.releaseFloatingMarker();
    });
    document.addEventListener('mousemove', this.onSelectedMove);
    document.addEventListener('mouseup', this.removeSelect);
    const { min = 0, max = 0, step = 1 } = option;
    this.min = min;
    this.max = max;
    this.step = step;
    this.markers = {};
  }

  destroy = (): void => {
    document.removeEventListener('mousemove', this.onSelectedMove);
    document.removeEventListener('mouseup', this.removeSelect);
  };

  toggle = (): void => {
    if (this.container.classList.contains('hidden')) {
      this.container.classList.remove('hidden');
      if (this.container.parentElement) {
        this.container.parentElement.style.height = `${
          this.container.parentElement.clientHeight + 12
        }px`;
      }
    } else {
      this.container.classList.add('hidden');
      if (this.container.parentElement) {
        this.container.parentElement.style.height = `${
          this.container.parentElement.clientHeight - 12
        }px`;
      }
    }
  };

  isEnabled = (): boolean => {
    return this.max > this.min;
  };

  adjustPos = (pos: number): number => {
    const width = this.container.clientWidth;
    if (width === 0) {
      return 0;
    }
    if (this.step <= 0) {
      return (pos / width) * 100;
    } else {
      let v = (pos / width) * (this.max - this.min);
      v = Math.round(v / this.step) * this.step;
      return (v / (this.max - this.min)) * 100;
    }
  };

  pos2value = (pos: number): number => {
    return this.min + (pos * (this.max - this.min)) / 100;
  };

  value2pos = (value: number): number => {
    return ((value - this.min) / (this.max - this.min)) * 100;
  };

  addRangeSelectedCallback = (callback: OnRangeSelect): void => {
    this.rangeSelectedCallbacks.push(callback);
  };

  removeRangeSelectedCallback = (callback: OnRangeSelect): void => {
    arrayRemove(this.rangeSelectedCallbacks, callback);
  };

  addMarkersChangeCallback = (callback: OnMarkersChange): void => {
    this.markersChangeCallbacks.push(callback);
  };

  removeMarkersChangeCallback = (callback: OnMarkersChange): void => {
    arrayRemove(this.markersChangeCallbacks, callback);
  };

  calcRange = (pos: number): [number, number] => {
    const res: [number, number] = [this.min, this.max];
    const value = this.pos2value(pos);
    for (const key of Object.keys(this.markers)) {
      const v = this.pos2value(Number.parseFloat(key));
      if (pos === v) {
        return [0, 0];
      } else if (value > v && v > res[0]) {
        res[0] = v;
      } else if (value < v && v < res[1]) {
        res[1] = v;
      }
    }
    return res;
  };

  makeFloatingMarker = (pos: number): void => {
    if (this.isEnabled()) {
      pos = this.adjustPos(pos);
      if (!this.floatingMarker) {
        this.floatingMarker = document.createElement('div');
        this.floatingMarker.classList.add('marker', 'floating');
        this.container.appendChild(this.floatingMarker);
      }
      this.floatingMarker.style.left = `${pos}%`;
      this.floatingMarker.style.translate = '-50%';
    }
  };

  releaseFloatingMarker = (): void => {
    if (this.floatingMarker) {
      this.container.removeChild(this.floatingMarker);
      this.floatingMarker = undefined;
    }
  };

  findMarkderKey = (marker: HTMLDivElement): number | undefined => {
    for (const key of Object.keys(this.markers)) {
      const pos = Number.parseFloat(key);
      if (marker === this.markers[pos]) {
        return pos;
      }
    }
    return undefined;
  };

  getMarkers = (): number[] => {
    return Object.keys(this.markers)
      .map((key) => {
        const pos = Number.parseFloat(key);
        return this.pos2value(pos);
      })
      .sort();
  };

  setMarkers = (markers: number[] | undefined | null): void => {
    if (!markers) {
      markers = [];
    }
    if (arrayEqual(this.getMarkers(), markers)) {
      return;
    }
    this.unselectRange();
    this.removeSelect();
    for (const key of Object.keys(this.markers)) {
      const marker = this.markers[key as any];
      this.removeMarkerByNode(marker, false);
    }
    for (const marker of markers) {
      this.addMarker(this.value2pos(marker), false);
    }
    this.execuateMarkersCallbacks();
  };

  execuateMarkersCallbacks = (): void => {
    const markers = this.getMarkers();
    for (const callback of this.markersChangeCallbacks) {
      callback(markers, this);
    }
  };

  removeMarkerByNode = (
    marker: HTMLDivElement,
    triggerCallback = true
  ): void => {
    const key = this.findMarkderKey(marker);
    if (key !== undefined) {
      delete this.markers[key];
      this.container.removeChild(marker);
      if (triggerCallback) {
        this.execuateMarkersCallbacks();
      }
    }
  };

  addMarker = (pos: number, triggerCallback = true): void => {
    if (this.isEnabled()) {
      let marker = this.markers[pos];
      if (!marker) {
        this.markers[pos] = marker = document.createElement('div');
        marker.setAttribute('draggable', 'false');
        marker.classList.add('marker');
        this.container.appendChild(marker);
        marker.style.left = `${pos}%`;
        marker.style.translate = '-50%';
        marker.addEventListener('click', (evt) => {
          evt.stopPropagation();
          if (evt.altKey) {
            this.removeMarkerByNode(marker);
          }
        });
        marker.addEventListener('mousedown', (evt) => {
          evt.stopPropagation();
          const key = this.findMarkderKey(marker);
          if (key !== undefined) {
            this.setSelect(key);
          }
        });
        marker.addEventListener('mouseup', () => {
          this.removeSelect();
        });
        if (triggerCallback) {
          this.execuateMarkersCallbacks();
        }
      }
    }
  };

  setSelect = (pos: number): void => {
    this.selectedKey = pos;
    const marker = this.markers[pos];
    if (marker) {
      marker.classList.add('selected');
    }
  };

  removeSelect = (): void => {
    if (this.selectedKey !== undefined) {
      const marker = this.markers[this.selectedKey];
      if (marker) {
        marker.classList.remove('selected');
      }
      this.selectedKey = undefined;
    }
  };

  canKeyMove = (posFrom: number, posTo: number): boolean => {
    if (posFrom === posTo) {
      return false;
    }
    if (posTo < 0 || posTo > 100) {
      return false;
    }
    const keys = Object.keys(this.markers);
    for (const key of keys) {
      const pos = Number.parseFloat(key);
      if (pos === posFrom) {
        continue;
      }
      if (pos === posTo) {
        return false;
      }
      if (pos < posFrom && posTo > posFrom) {
        continue;
      }
      if (pos > posFrom && posTo < posFrom) {
        continue;
      }
      if (pos < posFrom && pos > posTo) {
        return false;
      }
      if (pos > posFrom && pos < posTo) {
        return false;
      }
    }
    return true;
  };

  onSelectedMove = (evt: MouseEvent): void => {
    let pos = calcMouseOffsetX(evt, this.container);
    pos = this.adjustPos(pos);
    if (
      this.selectedKey !== undefined &&
      this.canKeyMove(this.selectedKey, pos)
    ) {
      const marker = this.markers[this.selectedKey];
      if (marker) {
        marker.style.left = `${pos}%`;
        marker.style.translate = '-50%';
        delete this.markers[this.selectedKey];
        this.updateRangeSelectBecauseOfKeyChagne(this.selectedKey, pos);
        this.selectedKey = pos;
        this.markers[pos] = marker;
        this.execuateMarkersCallbacks();
      }
    }
  };

  isRangeSelected = (range?: [number, number]): boolean => {
    if (!range) {
      range = this.selectedRange;
    }
    return range[1] > range[0];
  };

  updateRangeSelectBecauseOfKeyChagne = (
    posFrom: number,
    posTo: number
  ): void => {
    const valueFrom = this.pos2value(posFrom);
    if (
      this.isRangeSelected() &&
      (valueFrom === this.selectedRange[0] ||
        valueFrom === this.selectedRange[1])
    ) {
      const valueTo = this.pos2value(posTo);
      let valueOther: number;
      if (valueFrom === this.selectedRange[0]) {
        valueOther = this.selectedRange[1];
      } else {
        valueOther = this.selectedRange[0];
      }
      const newRange: [number, number] =
        valueTo <= valueOther ? [valueTo, valueOther] : [valueOther, valueTo];
      this.updateRangeSelect(newRange);
    }
  };

  updateRangeSelect = (newRange: [number, number]): void => {
    if (this.isRangeSelected(newRange)) {
      const cWidth = this.container.clientWidth;
      const left = ((newRange[0] - this.min) / (this.max - this.min)) * cWidth;
      const right = ((newRange[1] - this.min) / (this.max - this.min)) * cWidth;
      this.rangeMasker.style.left = `${left}px`;
      this.rangeMasker.style.width = `${right - left}px`;
      this.rangeMasker.classList.remove('hidden');
    }
    this.selectedRange = newRange;
    for (const callback of this.rangeSelectedCallbacks) {
      callback(this.selectedRange, this);
    }
  };

  onMouseRangeSelect = (evt: MouseEvent): void => {
    if (this.selectedKey !== undefined) {
      // when moving key point, do nothing.
      return;
    }
    const cWidth = this.container.clientWidth;
    if (cWidth === 0) {
      return;
    }
    const pos = (calcMouseOffsetX(evt, this.container) / cWidth) * 100;
    const range = this.calcRange(pos);
    this.updateRangeSelect(range);
  };

  selectRange = (range: [number, number]): void => {
    if (arrayEqual(this.selectedRange, range)) {
      return;
    }
    const posFrom = this.value2pos(range[0]);
    const posTo = this.value2pos(range[1]);
    if (this.markers[posFrom] && this.markers[posTo]) {
      this.updateRangeSelect(range);
    }
  };

  unselectRange = (): void => {
    this.rangeMasker.style.left = '0px';
    this.rangeMasker.style.width = '0px';
    this.rangeMasker.classList.add('hidden');
    this.selectedRange = [0, 0];
    for (const callback of this.rangeSelectedCallbacks) {
      callback(this.selectedRange, this);
    }
  };
}
