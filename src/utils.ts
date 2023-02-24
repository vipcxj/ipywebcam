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

export function arrayIndexOf<T>(arr: T[], target: T): number {
  for (let i = 0; i < arr.length; ++i) {
    if (arr[i] === target) {
      return i;
    }
  }
  return -1;
}

export function arrayRemove<T>(arr: T[], target: T): boolean {
  const index = arrayIndexOf(arr, target);
  if (index !== -1) {
    arr.splice(index, 1);
    return true;
  } else {
    return false;
  }
}

export function arrayEqual<T>(arr1?: T[], arr2?: T[]): boolean {
  if (arr1 === arr2) {
    return true;
  }
  return (
    Array.isArray(arr1) &&
    Array.isArray(arr2) &&
    arr1.length === arr2.length &&
    arr1.every((val, index) => val === arr2[index])
  );
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
