/* eslint-disable @typescript-eslint/no-non-null-assertion */
import { calcMouseOffsetX } from './utils';

export interface RangeBarOption {
  max?: number;
  min?: number;
  step?: number;
}

export class RangeBar {
  container: HTMLDivElement;
  min: number;
  max: number;
  step: number;

  markers: { [key: number]: HTMLDivElement };
  floatingMarker?: HTMLDivElement;
  selected?: number;
  rangeMasker: HTMLDivElement;

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
        this.addMarker(evt.offsetX);
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

  findMarkderKey = (marker: HTMLDivElement): number => {
    for (const key of Object.keys(this.markers)) {
      const pos = Number.parseFloat(key);
      if (marker === this.markers[pos]) {
        return pos;
      }
    }
    return 0;
  };

  addMarker = (pos: number): void => {
    if (this.isEnabled()) {
      pos = this.adjustPos(pos);
      let marker = this.markers[pos];
      if (!marker) {
        this.markers[pos] = marker = document.createElement('div');
        marker.classList.add('marker');
        this.container.appendChild(marker);
        marker.style.left = `${pos}%`;
        marker.style.translate = '-50%';
        marker.addEventListener('click', (evt) => {
          if (evt.altKey) {
            const key = this.findMarkderKey(marker);
            delete this.markers[key];
            this.container.removeChild(marker);
          }
        });
        marker.addEventListener('mousedown', () => {
          const key = this.findMarkderKey(marker);
          this.setSelect(key);
        });
        marker.addEventListener('mouseup', () => {
          this.removeSelect();
        });
      }
    }
  };

  setSelect = (pos: number): void => {
    this.selected = pos;
    const marker = this.markers[pos];
    if (marker) {
      marker.classList.add('selected');
    }
  };

  removeSelect = (): void => {
    if (this.selected) {
      const marker = this.markers[this.selected];
      if (marker) {
        marker.classList.remove('selected');
      }
      this.selected = undefined;
    }
  };

  onSelectedMove = (evt: MouseEvent): void => {
    let pos = calcMouseOffsetX(evt, this.container);
    pos = this.adjustPos(pos);
    if (this.selected && this.selected !== pos) {
      const marker = this.markers[this.selected];
      if (marker) {
        marker.style.left = `${pos}%`;
        marker.style.translate = '-50%';
        delete this.markers[this.selected];
        this.selected = pos;
        this.markers[pos] = marker;
      }
    }
  };

  onMouseRangeSelect = (evt: MouseEvent): void => {
    const cWidth = this.container.clientWidth;
    if (cWidth === 0) {
      return;
    }
    const pos = (calcMouseOffsetX(evt, this.container) / cWidth) * 100;
    const range = this.calcRange(pos);
    if (range[0] < range[1]) {
      const left = ((range[0] - this.min) / (this.max - this.min)) * cWidth;
      const right = ((range[1] - this.min) / (this.max - this.min)) * cWidth;
      this.rangeMasker.style.left = `${left}px`;
      this.rangeMasker.style.width = `${right - left}px`;
      this.rangeMasker.classList.remove('hidden');
    }
  };

  unselectRange = (): void => {
    this.rangeMasker.style.left = '0px';
    this.rangeMasker.style.width = '0px';
    this.rangeMasker.classList.add('hidden');
  };
}
