/** True-scale view (SRS FR-11): the browser cannot know the physical screen size, so the user
 *  matches a bank card to the screen once. That gives pixels per millimetre. */
export const CARD_WIDTH_MM = 85.6; // ISO/IEC 7810 ID-1
export const CARD_HEIGHT_MM = 53.98;
export const MIN_PX_PER_MM = 2;
export const MAX_PX_PER_MM = 10;
export const DEFAULT_PX_PER_MM = 96 / 25.4; // a CSS pixel guess until the user calibrates
const STORAGE_KEY = "pxPerMm";

export const clampPxPerMm = (v: number): number =>
  Math.min(MAX_PX_PER_MM, Math.max(MIN_PX_PER_MM, v));

export const pxPerMmFromCardWidth = (cardWidthPx: number): number =>
  clampPxPerMm(cardWidthPx / CARD_WIDTH_MM);

/** Camera frustum in mm so that one millimetre is exactly pxPerMm pixels on screen. */
export function orthoFrustum(widthPx: number, heightPx: number, pxPerMm: number) {
  const halfW = widthPx / pxPerMm / 2;
  const halfH = heightPx / pxPerMm / 2;
  return { left: -halfW, right: halfW, top: halfH, bottom: -halfH };
}

export const mmToPx = (mm: number, pxPerMm: number): number => mm * pxPerMm;

export function loadPxPerMm(storage: Pick<Storage, "getItem">): number {
  try {
    const v = Number(storage.getItem(STORAGE_KEY));
    return Number.isFinite(v) && v > 0 ? clampPxPerMm(v) : DEFAULT_PX_PER_MM;
  } catch {
    return DEFAULT_PX_PER_MM;
  }
}

export function savePxPerMm(storage: Pick<Storage, "setItem">, v: number): void {
  try {
    storage.setItem(STORAGE_KEY, String(v));
  } catch {
    /* storage unavailable: the value just will not persist */
  }
}
