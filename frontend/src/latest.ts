/** Ignore responses that arrive out of order: only the most recent request may update the screen. */
export function makeLatestGuard() {
  let current = 0;
  return {
    next: (): number => ++current,
    isLatest: (token: number): boolean => token === current,
  };
}
