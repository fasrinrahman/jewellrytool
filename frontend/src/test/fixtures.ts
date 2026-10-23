import type { BuildResponse, RingParams, Rules, Sizes } from "../types";

export const RULES: Rules = {
  verified_by_jeweler: false,
  metals: {
    silver_925: { density_g_cm3: 10.36, min_wall_mm: 0.8, min_prong_diameter_mm: 0.8, min_band_thickness_mm: 1.2, band_width_range_mm: [1.5, 8] },
    gold_14k: { density_g_cm3: 13, min_wall_mm: 0.8, min_prong_diameter_mm: 0.8, min_band_thickness_mm: 1.2, band_width_range_mm: [1.5, 8] },
  },
  stone_shapes: { round: { size_range_mm: [3, 10], prong_counts: [4, 6] } },
  tolerances: { stl_step_volume_pct: 0.5 },
};

export const SIZES: Sizes = { mm: 17.32, us: 7, uk: "N\u00bd", eu: 54 };

export const PARAMS: RingParams = {
  metal: "silver_925", ring_size_mm: 17.32, band_width_mm: 3, band_thickness_mm: 1.8,
  stone_shape: "round", stone_size_mm: 6, prong_count: 4, prong_diameter_mm: 1, finish: "polished",
};

export const MESH = { vertices: [0, 0, 0, 1, 0, 0, 0, 1, 0], indices: [0, 1, 2] };

export function goodBuild(weight = 4.9): BuildResponse {
  return {
    params: PARAMS,
    exportable: true,
    report: [
      { check_id: "L1-BAND-WIDTH", layer: 1, status: "pass", message: "The band width of 3 mm is within range.", fix: null },
      { check_id: "RULES-UNVERIFIED", layer: null, status: "unverified", message: "The design rules have not been reviewed by a jeweler yet.", fix: null },
    ],
    mesh: MESH,
    bbox_mm: { min: [-10, -10, -2], max: [10, 14, 2] },
    numbers: {
      weight_g: weight, density_g_cm3: 10.36, currency: "USD", cost_low: 3.9, cost_high: 5.9,
      cost_text: "USD 3.92 to 5.88 for the metal only (stone, labor, casting, and finishing are not included)",
      price_source: "PLACEHOLDER", price_as_of: "2026-10-14", prices_verified: false,
    },
    sizes: SIZES,
    suggestion: null,
  };
}

export function badBuild(): BuildResponse {
  const fixed = { ...PARAMS, prong_diameter_mm: 0.8 };
  return {
    params: { ...PARAMS, prong_diameter_mm: 0.4 },
    exportable: false,
    report: [{ check_id: "L1-PRONG-DIAMETER", layer: 1, status: "fail",
      message: "The prongs are 0.4 mm thick, so they could bend or break.", fix: { field: "prong_diameter_mm", value: 0.8 } }],
    mesh: null, bbox_mm: null, numbers: null, sizes: SIZES,
    suggestion: { params: fixed, changes: [{ field: "prong_diameter_mm", old: 0.4, new: 0.8 }] },
  };
}
