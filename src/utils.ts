export function arrayInclude<T>(arr: T[], target: T): boolean {
  return !!~arr.indexOf(target);
}

export function arrayFind<T>(
  arr: T[],
  cond: (v: T, idx: number) => boolean
): T | undefined {
  for (let i = 0; i < arr.length; ++i) {
    const e = arr[i];
    if (cond(e, i)) {
      return e;
    }
  }
  return undefined;
}

export function isMac(): boolean {
  return window.navigator.userAgent.indexOf('Mac') !== -1;
}

export function calcPageX(element: Element): number {
  const { left } = element.getBoundingClientRect();
  return left + document.body.scrollLeft;
}

export function calcMouseOffsetX(evt: MouseEvent, target: Element): number {
  return evt.pageX - calcPageX(target);
}
