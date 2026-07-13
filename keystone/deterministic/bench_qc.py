"""
keystone.deterministic.bench_qc
==============================
Deterministic quality-control for bench data — the numbers a Reviewer
uses to downgrade a hypothesis whose grounding rests on the experiment.

Rule 7 applies absolutely: this module owns every number. Claude may
narrate the result but never sets the verdict. Every threshold is a
NAMED CONSTANT with a citation; nothing is a magic number.

CSV format (Bio-Rad / generic 96-well plate reader):

    # any comment line starting with '#'
    standard,<position>,<concentration>,<reading>
    sample,<position>,<sample_id>,<reading>

Positions are 8x12 grid coordinates (A1..H12).
"""
from __future__ import annotations

import csv
import io
import re
import statistics
from dataclasses import dataclass


# --- QC thresholds (named constants, cite-able) -----------------------------
R2_LOAD_BEARING = 0.98      # Ekins & Chu 1988; FDA Bioanalytical 2018
REPLICATE_CV_MAX = 0.15     # FDA Bioanalytical Method Validation, 2018
EDGE_EFFECT_MAX = 0.15      # common HTS screen QC
MISSING_WELLS_MAX = 4       # common 96-well plate QC
BREACH_HARD_MULT = 2.0      # >=2x breach severity triggers REJECTED

# --- 96-well plate geometry -------------------------------------------------
PLATE_WELLS = 96
ROWS = tuple("ABCDEFGH")
COLS = tuple(range(1, 13))
EDGE_ROWS = frozenset({"A", "H"})
EDGE_COLS = frozenset({1, 12})


@dataclass(frozen=True)
class Well:
    kind: str        # 'standard' or 'sample'
    position: str    # e.g. 'A1'
    label: str       # concentration string (standards) or sample id (samples)
    reading: float


@dataclass(frozen=True)
class BenchPlate:
    wells: tuple
    n_expected_wells: int = PLATE_WELLS


@dataclass(frozen=True)
class QCCheck:
    name: str
    value: float
    threshold: float
    breached: bool
    breach_severity: float   # (value - threshold) / threshold when breached
    detail: str
    citation: str


_EXPECTED_RE = re.compile(r"#\s*(?:expected_)?wells\s*:\s*(\d+)", re.IGNORECASE)


def parse_csv(text: str) -> BenchPlate:
    """Parse a plate-reader CSV. A comment line ``# expected_wells: N`` (or
    ``# wells: N``) declares the intended plate size so the missing-wells
    check has a target; without it we default to the number of wells found
    and do NOT invent a missing count (honest: we can't know the target)."""
    wells = []
    declared = None
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            m = _EXPECTED_RE.search(stripped)
            if m:
                declared = int(m.group(1))
            continue
        for row in csv.reader(io.StringIO(raw_line)):
            if not row or not row[0].strip():
                continue
            if len(row) < 4:
                continue
            kind = row[0].strip().lower()
            if kind not in ("standard", "sample"):
                continue
            pos = row[1].strip().upper()
            label = row[2].strip()
            try:
                reading = float(row[3].strip())
            except ValueError:
                continue
            wells.append(Well(kind=kind, position=pos, label=label,
                              reading=reading))
    expected = declared if declared is not None else len(wells)
    return BenchPlate(wells=tuple(wells), n_expected_wells=expected)


def _linreg_r2(xs: list, ys: list) -> float:
    if len(xs) < 3:
        return 0.0
    x_mean = statistics.mean(xs)
    y_mean = statistics.mean(ys)
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    denom_x = sum((x - x_mean) ** 2 for x in xs)
    denom_y = sum((y - y_mean) ** 2 for y in ys)
    if denom_x == 0 or denom_y == 0:
        return 0.0
    slope = num / denom_x
    intercept = y_mean - slope * x_mean
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    return max(0.0, 1.0 - ss_res / denom_y)


def check_standard_curve(plate: BenchPlate) -> QCCheck:
    """R² of the standard curve — load-bearing quantification needs >= 0.98."""
    standards = [w for w in plate.wells if w.kind == "standard"]
    xs, ys = [], []
    for w in standards:
        try:
            xs.append(float(w.label))
            ys.append(w.reading)
        except ValueError:
            continue
    r2 = _linreg_r2(xs, ys) if len(xs) >= 3 else 0.0
    breached = r2 < R2_LOAD_BEARING
    severity = (R2_LOAD_BEARING - r2) / R2_LOAD_BEARING if breached else 0.0
    return QCCheck(
        name="standard_curve_r2",
        value=round(r2, 4),
        threshold=R2_LOAD_BEARING,
        breached=breached,
        breach_severity=severity,
        detail=(f"Standard curve R² = {r2:.3f} across {len(xs)} calibrator "
                f"point(s); load-bearing quantification requires "
                f"≥ {R2_LOAD_BEARING}."),
        citation="Ekins & Chu 1988; FDA Bioanalytical Method Validation 2018",
    )


def check_replicate_cv(plate: BenchPlate) -> QCCheck:
    """Worst well-to-well CV across sample replicate groups. Target <= 15%."""
    groups: dict = {}
    for w in plate.wells:
        if w.kind != "sample":
            continue
        groups.setdefault(w.label, []).append(w.reading)
    cvs = []
    worst_group = ""
    for label, readings in groups.items():
        if len(readings) < 2:
            continue
        mean = statistics.mean(readings)
        if mean == 0:
            continue
        sd = statistics.pstdev(readings)
        cv = sd / mean
        cvs.append(cv)
        if cv == max(cvs):
            worst_group = label
    max_cv = max(cvs) if cvs else 0.0
    breached = max_cv > REPLICATE_CV_MAX
    severity = (max_cv - REPLICATE_CV_MAX) / REPLICATE_CV_MAX if breached else 0.0
    return QCCheck(
        name="replicate_cv",
        value=round(max_cv, 4),
        threshold=REPLICATE_CV_MAX,
        breached=breached,
        breach_severity=severity,
        detail=(f"Worst replicate CV = {max_cv * 100:.1f}%"
                + (f" (group {worst_group})" if worst_group else "")
                + f" across {len(cvs)} sample group(s); "
                + f"target ≤ {REPLICATE_CV_MAX * 100:.0f}%."),
        citation="FDA Bioanalytical Method Validation 2018 §V",
    )


def check_edge_effect(plate: BenchPlate) -> QCCheck:
    """Edge wells vs interior wells; |edge - interior| / interior > 15% flags."""
    edge, interior = [], []
    for w in plate.wells:
        if w.kind != "sample":
            continue
        row = w.position[:1]
        try:
            col = int(w.position[1:])
        except ValueError:
            continue
        is_edge = row in EDGE_ROWS or col in EDGE_COLS
        (edge if is_edge else interior).append(w.reading)
    if not edge or not interior:
        return QCCheck(
            name="edge_effect",
            value=0.0,
            threshold=EDGE_EFFECT_MAX,
            breached=False,
            breach_severity=0.0,
            detail="Edge effect not evaluable (need samples at both edge and "
                   "interior positions).",
            citation="Standard 96-well plate HTS QC",
        )
    med_edge = statistics.median(edge)
    med_int = statistics.median(interior)
    if med_int == 0:
        return QCCheck(
            name="edge_effect",
            value=0.0,
            threshold=EDGE_EFFECT_MAX,
            breached=False,
            breach_severity=0.0,
            detail="Edge effect not evaluable (interior median is zero).",
            citation="Standard 96-well plate HTS QC",
        )
    ratio = abs(med_edge - med_int) / med_int
    breached = ratio > EDGE_EFFECT_MAX
    severity = (ratio - EDGE_EFFECT_MAX) / EDGE_EFFECT_MAX if breached else 0.0
    return QCCheck(
        name="edge_effect",
        value=round(ratio, 4),
        threshold=EDGE_EFFECT_MAX,
        breached=breached,
        breach_severity=severity,
        detail=(f"Edge vs interior median difference = {ratio * 100:.1f}% "
                f"(edge={med_edge:.3f}, interior={med_int:.3f}); "
                f"target ≤ {EDGE_EFFECT_MAX * 100:.0f}%."),
        citation="Standard 96-well plate HTS QC",
    )


def check_missing_wells(plate: BenchPlate) -> QCCheck:
    n_missing = max(0, plate.n_expected_wells - len(plate.wells))
    breached = n_missing >= MISSING_WELLS_MAX
    severity = (n_missing - MISSING_WELLS_MAX + 1) / MISSING_WELLS_MAX if breached else 0.0
    return QCCheck(
        name="missing_wells",
        value=float(n_missing),
        threshold=float(MISSING_WELLS_MAX),
        breached=breached,
        breach_severity=severity,
        detail=(f"{n_missing} of {plate.n_expected_wells} wells missing or "
                f"unparseable; target < {MISSING_WELLS_MAX}."),
        citation="Common 96-well plate QC",
    )


def run_qc(plate: BenchPlate) -> list:
    return [
        check_standard_curve(plate),
        check_replicate_cv(plate),
        check_edge_effect(plate),
        check_missing_wells(plate),
    ]
