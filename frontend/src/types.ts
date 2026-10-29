export type Status = "pass" | "warn" | "fail" | "unverified";

export interface CheckResult {
  check_id: string;
  layer: number | null;
  status: Status;
  message: string;
  fix: { field: string; value: number } | null;
}

export interface RingParams {
  metal: string;
  ring_size_mm: number;
  band_width_mm: number;
  band_thickness_mm: number;
  stone_shape: "round";
  stone_size_mm: number;
  prong_count: number;
  prong_diameter_mm: number;
  finish: "polished" | "satin";
}

/** Everything except ring size, which comes from the size converter. */
export type FormParams = Omit<RingParams, "ring_size_mm">;

export interface MeshData {
  vertices: number[]; // flat [x, y, z, ...] in millimetres
  indices: number[]; // flat [i, j, k, ...]
}

export interface Numbers {
  weight_g: number;
  density_g_cm3: number;
  currency: string;
  cost_low: number | null;
  cost_high: number | null;
  cost_text: string;
  price_source: string;
  price_as_of: string;
  prices_verified: boolean;
}

export interface Sizes {
  mm: number;
  us: number;
  uk: string;
  eu: number;
}

export interface Suggestion {
  params: RingParams;
  changes: { field: string; old: number; new: number }[];
}

export interface BuildResponse {
  params: RingParams;
  exportable: boolean;
  report: CheckResult[];
  mesh: MeshData | null;
  bbox_mm: { min: number[]; max: number[] } | null;
  numbers: Numbers | null;
  sizes: Sizes | null;
  suggestion: Suggestion | null;
}

export interface Rules {
  verified_by_jeweler: boolean;
  ring_size_range_mm: [number, number];
  metals: Record<
    string,
    {
      density_g_cm3: number;
      min_wall_mm: number;
      min_prong_diameter_mm: number;
      min_band_thickness_mm: number;
      band_width_range_mm: [number, number];
      max_band_thickness_mm: number;
      max_prong_diameter_mm: number;
    }
  >;
  stone_shapes: Record<
    string,
    { size_range_mm: [number, number]; prong_counts: number[]; max_prong_coverage: number }
  >;
  tolerances: Record<string, number>;
}

export type SizeSystem = "us" | "uk" | "eu" | "mm";
export interface SizeInput {
  system: SizeSystem;
  value: string;
}
