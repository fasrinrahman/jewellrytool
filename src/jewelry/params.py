"""Ring parameter schema: the single contract between AI layer, validator and CAD engine.

Two kinds of limits exist on purpose:
- Hard limits here are generous. They only stop absurd or malicious input (infinity, 1e9 mm,
  a 5000 character metal name) from ever reaching the CAD engine.
- Design rules in rules.yaml are the real manufacturing limits. They fail with a plain explanation.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

HARD_MAX_MM = 100.0      # nothing in a ring is larger than this
HARD_MAX_PRONGS = 50


def _mm(description: str = ""):
    return Field(gt=0, le=HARD_MAX_MM, allow_inf_nan=False, description=description)


class RingParams(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected (FR-12)

    metal: str = Field(min_length=1, max_length=40)
    ring_size_mm: float = _mm("Inner diameter in mm")
    band_width_mm: float = _mm()
    band_thickness_mm: float = _mm()
    stone_shape: Literal["round"]
    stone_size_mm: float = _mm()
    prong_count: int = Field(gt=0, le=HARD_MAX_PRONGS)
    prong_diameter_mm: float = _mm()
    finish: Literal["polished", "satin"] = "polished"  # listed on the spec sheet; no effect on geometry
