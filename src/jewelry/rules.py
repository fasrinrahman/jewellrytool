"""Design rules are read from a config file, never hard-coded (FR-03)."""
from pathlib import Path
import yaml

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "rules" / "rules.yaml"
REQUIRED_KEYS = ("metals", "stone_shapes", "tolerances")


def load_rules(path=None) -> dict:
    with open(path or DEFAULT_RULES_PATH, encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    missing = [k for k in REQUIRED_KEYS if k not in rules]
    if missing:
        raise ValueError(f"rules file is missing: {', '.join(missing)}")
    return rules


DEFAULT_PRICES_PATH = Path(__file__).resolve().parents[2] / "rules" / "prices.yaml"
PRICE_KEYS = ("currency", "source", "as_of", "metals")


def load_prices(path=None) -> dict:
    """Metal prices come from a config file that names its source and date (NFR-03)."""
    with open(path or DEFAULT_PRICES_PATH, encoding="utf-8") as f:
        prices = yaml.safe_load(f)
    missing = [k for k in PRICE_KEYS if k not in prices]
    if missing:
        raise ValueError(f"prices file is missing: {', '.join(missing)}")
    return prices
