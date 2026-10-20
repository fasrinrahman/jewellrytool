"""Validation report: one entry per check, in plain language (FR-05)."""
from dataclasses import dataclass, asdict
from typing import Optional

PASS, WARN, FAIL, UNVERIFIED = "pass", "warn", "fail", "unverified"


@dataclass
class CheckResult:
    check_id: str
    layer: Optional[int]
    status: str            # pass, warn, fail, or unverified
    message: str           # plain language, no field names
    fix: Optional[dict] = None   # {"field": ..., "value": ...} when a safe value exists


@dataclass
class Report:
    results: list

    @property
    def exportable(self) -> bool:
        """A design is exportable only when no check fails (NFR-01)."""
        return not any(r.status == FAIL for r in self.results)

    def with_status(self, status: str) -> list:
        return [r for r in self.results if r.status == status]

    def to_dict(self) -> dict:
        return {"exportable": self.exportable,
                "results": [asdict(r) for r in self.results]}

    def to_text(self) -> str:
        tags = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL", UNVERIFIED: "NOT CHECKED"}
        lines = [f"[{tags[r.status]}] {r.message}" for r in self.results]
        lines.append("Ready to export." if self.exportable
                     else "Not ready to export: fix the failed checks first.")
        return "\n".join(lines)
