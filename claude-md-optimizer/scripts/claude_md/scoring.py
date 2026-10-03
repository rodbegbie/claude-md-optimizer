from collections import Counter
from dataclasses import dataclass

from claude_md.findings import REGISTRY, Finding

MAX_SCORE = 100


@dataclass(frozen=True)
class Deduction:
    check_id: str
    count: int
    points: int
    capped: bool


@dataclass(frozen=True)
class Score:
    value: int
    deductions: list[Deduction]


def score(findings: list[Finding]) -> Score:
    counts = Counter(f.check_id for f in findings)
    deductions: list[Deduction] = []
    for check_id in sorted(counts):
        spec = REGISTRY.get(check_id)
        if spec is None:
            raise ValueError(f"finding from unregistered check: {check_id}")
        raw = spec.weight * counts[check_id]
        deductions.append(
            Deduction(check_id, counts[check_id], min(spec.cap, raw), raw > spec.cap)
        )
    total = sum(d.points for d in deductions)
    return Score(max(0, MAX_SCORE - total), deductions)
