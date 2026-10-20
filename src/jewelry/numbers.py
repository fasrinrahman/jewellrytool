"""Metal weight and cost range (FR-08, NFR-02, NFR-03)."""
from dataclasses import dataclass
from typing import Optional
from .params import RingParams


@dataclass
class DesignNumbers:
    volume_cm3: float
    density_g_cm3: float
    weight_g: float
    currency: str
    cost_low: Optional[float]
    cost_high: Optional[float]
    price_source: str
    price_as_of: str
    prices_verified: bool

    def cost_text(self) -> str:
        if self.cost_low is None:
            return "Not estimated: there is no price for this metal in the price file."
        return (f"{self.currency} {self.cost_low:.2f} to {self.cost_high:.2f} for the metal only "
                "(stone, labor, casting, and finishing are not included)")


def design_numbers(p: RingParams, volume_mm3: float, rules: dict, prices: dict) -> DesignNumbers:
    if p.metal not in rules["metals"]:
        raise ValueError(f"Unknown metal '{p.metal}'.")
    density = rules["metals"][p.metal]["density_g_cm3"]
    volume_cm3 = volume_mm3 / 1000
    weight = volume_cm3 * density
    price = prices["metals"].get(p.metal)
    low = high = None
    if price:
        per_g_low, per_g_high = price["price_per_gram"]
        low, high = weight * per_g_low, weight * per_g_high
    return DesignNumbers(volume_cm3, density, weight, prices["currency"], low, high,
                         prices["source"], str(prices["as_of"]), bool(prices.get("verified")))
