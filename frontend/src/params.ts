import type { FormParams, SizeInput } from "./types";

export const DEFAULT_FORM: FormParams = {
  metal: "silver_925",
  band_width_mm: 3.0,
  band_thickness_mm: 1.8,
  stone_shape: "round",
  stone_size_mm: 6.0,
  prong_count: 4,
  prong_diameter_mm: 1.0,
  finish: "polished",
};

export const DEFAULT_SIZE_INPUT: SizeInput = { system: "us", value: "7" };

export const metalLabel = (metal: string): string => metal.replace(/_/g, " ");

export const STATUS_LABEL = {
  pass: "PASS",
  warn: "WARN",
  fail: "FAIL",
  unverified: "NOT CHECKED",
} as const;
