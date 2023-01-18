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
