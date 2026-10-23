import { describe, expect, it, vi } from "vitest";
import {
  CARD_WIDTH_MM, DEFAULT_PX_PER_MM, MAX_PX_PER_MM, MIN_PX_PER_MM, clampPxPerMm, loadPxPerMm,
  mmToPx, orthoFrustum, pxPerMmFromCardWidth, savePxPerMm,
} from "./trueScale";

describe("true-scale maths (FR-11)", () => {
  it("a bank card drawn 342.4 px wide means 4 px per mm", () => {
    expect(pxPerMmFromCardWidth(CARD_WIDTH_MM * 4)).toBeCloseTo(4, 6);
  });

  it("keeps the scale inside sensible limits", () => {
    expect(clampPxPerMm(0.1)).toBe(MIN_PX_PER_MM);
    expect(clampPxPerMm(100)).toBe(MAX_PX_PER_MM);
    expect(clampPxPerMm(5)).toBe(5);
  });

  it("frustum gives exactly pxPerMm pixels per millimetre", () => {
    const f = orthoFrustum(800, 600, 4);
    expect(f.right - f.left).toBeCloseTo(200); // 800 px / 4 px per mm
    expect(f.top - f.bottom).toBeCloseTo(150); // 600 px / 4 px per mm
    expect(f.left).toBeCloseTo(-f.right);
    expect(f.bottom).toBeCloseTo(-f.top);
  });

  it("a 20 mm scale bar is 20 times the scale in pixels", () => {
    expect(mmToPx(20, 3.78)).toBeCloseTo(75.6);
  });

  it("a 20.9 mm ring is drawn 83.6 px wide at 4 px per mm", () => {
    expect(mmToPx(20.9, 4)).toBeCloseTo(83.6);
  });
});

describe("saved calibration", () => {
  it("falls back to the default when nothing is saved or the value is bad", () => {
    expect(loadPxPerMm({ getItem: () => null })).toBeCloseTo(DEFAULT_PX_PER_MM);
    expect(loadPxPerMm({ getItem: () => "abc" })).toBeCloseTo(DEFAULT_PX_PER_MM);
    expect(loadPxPerMm({ getItem: () => "-3" })).toBeCloseTo(DEFAULT_PX_PER_MM);
  });

  it("loads a saved value and clamps it", () => {
    expect(loadPxPerMm({ getItem: () => "4.25" })).toBeCloseTo(4.25);
    expect(loadPxPerMm({ getItem: () => "99" })).toBe(MAX_PX_PER_MM);
  });

  it("survives storage that throws", () => {
    const broken = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
    expect(loadPxPerMm(broken)).toBeCloseTo(DEFAULT_PX_PER_MM);
    expect(() => savePxPerMm(broken, 4)).not.toThrow();
  });

  it("saves the value as text", () => {
    const setItem = vi.fn();
    savePxPerMm({ setItem }, 4.5);
    expect(setItem).toHaveBeenCalledWith("pxPerMm", "4.5");
  });
});
