"""Export a design: STL, STEP and spec sheet, only if every check passes (FR-09, FR-10, NFR-01)."""
from dataclasses import dataclass
from pathlib import Path
from .engine import build_ring
from .export import export_files
from .numbers import DesignNumbers, design_numbers
from .params import RingParams
from .report import Report
from .rules import load_prices, load_rules
from .spec_sheet import build_spec_sheet
from .validate import validate


class ExportRefused(Exception):
    """Raised when a check fails. The report says why, in plain language."""
    def __init__(self, report: Report):
        super().__init__("Export refused: a check failed.")
        self.report = report


@dataclass
class ExportResult:
    stl: Path
    step: Path
    spec_sheet: Path
    numbers: DesignNumbers
    report: Report


def export_design(p: RingParams, folder, rules: dict = None, prices: dict = None,
                  today=None) -> ExportResult:
    rules = rules or load_rules()
    prices = prices or load_prices()
    report = validate(p, rules)
    if not report.exportable:
        raise ExportRefused(report)          # nothing is written
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    shape = build_ring(p)
    export_files(shape, folder / "ring")
    numbers = design_numbers(p, shape.val().Volume(), rules, prices)
    sheet = build_spec_sheet(p, report, numbers, rules, folder / "ring_spec.pdf", today)
    return ExportResult(folder / "ring.stl", folder / "ring.step", sheet, numbers, report)
