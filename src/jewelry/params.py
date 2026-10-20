"""Ring parameter schema: the single contract between AI layer, validator and CAD engine."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class RingParams(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected (FR-12)

    metal: str
    ring_size_mm: float = Field(gt=0, description="Inner diameter in mm")
    band_width_mm: float = Field(gt=0)
    band_thickness_mm: float = Field(gt=0)
    stone_shape: Literal["round"]
    stone_size_mm: float = Field(gt=0)
    prong_count: int = Field(gt=0)
    prong_diameter_mm: float = Field(gt=0)
