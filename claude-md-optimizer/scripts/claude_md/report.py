from dataclasses import asdict
from pathlib import Path

from claude_md.findings import Finding
from claude_md.model import LoadedFile, Totals
from claude_md.scoring import Score

RULE = "=" * 60
DIVIDER = "-" * 60


def _sort_key(finding: Finding) -> tuple:
    return (
        finding.check_id,
        str(finding.path or ""),
        finding.line or 0,
        finding.message,
    )


def file_entries(files: list[LoadedFile]) -> list[dict]:
    return [
        {
            "path": str(f.path),
            "scope": str(f.scope),
            "mode": str(f.mode),
            "order": f.order,
            "lines": f.lines,
            "bytes": f.bytes,
            "tokens": f.tokens,
            "notes": list(f.notes),
            "paths": f.paths,
            "imported_by": str(f.imported_by) if f.imported_by else None,
            "external": f.external,
        }
        for f in files
    ]


def finding_entry(finding: Finding) -> dict:
    return {
        "check_id": finding.check_id,
        "severity": finding.severity,
        "path": str(finding.path) if finding.path else None,
        "line": finding.line,
        "message": finding.message,
        "fix": finding.fix,
        "source": {"kind": finding.source.kind, "url": finding.source.url},
    }


def to_json_data(
    files: list[LoadedFile],
    totals: Totals,
    findings: list[Finding],
    score: Score,
    unverified: list[str],
    memory_path: Path,
    memory_found: bool,
) -> dict:
    return {
        "files": file_entries(files),
        "totals": asdict(totals),
        "findings": [finding_entry(f) for f in sorted(findings, key=_sort_key)],
        "score": {
            "value": score.value,
            "deductions": [asdict(d) for d in score.deductions],
        },
        "unverified": unverified,
        "memory_directory": {"path": str(memory_path), "found": memory_found},
    }


def _render_finding(finding: Finding) -> list[str]:
    where = ""
    if finding.path and str(finding.path) not in finding.message:
        line = f":{finding.line}" if finding.line else ""
        where = f" ({finding.path}{line})"
    lines = [f"    [{finding.severity}] {finding.check_id}: {finding.message}{where}"]
    lines.append(f"        Fix: {finding.fix}")
    if finding.source.url:
        lines.append(f"        Docs: {finding.source.url}")
    return lines


def _render_group(title: str, findings: list[Finding]) -> list[str]:
    lines = [f"  {title} ({len(findings)}):"]
    if not findings:
        lines.append("    none")
    for finding in sorted(findings, key=_sort_key):
        lines.extend(_render_finding(finding))
    lines.append("")
    return lines


def render(
    files: list[LoadedFile],
    totals: Totals,
    findings: list[Finding],
    score: Score,
    unverified: list[str],
    project_dir: Path,
    memory_path: Path,
    memory_found: bool,
) -> str:
    memory_line = f"  Memory directory: {memory_path}" + (
        "" if memory_found else " (not found)"
    )
    out = [RULE, "  CLAUDE.md Optimization Report", RULE, ""]
    if not files:
        out += [f"  No instruction files found for {project_dir}.", memory_line]
        return "\n".join(out)

    out += [
        "  Context load (estimated tokens):",
        f"    Always-on:   ~{totals.always}",
        f"    Conditional: ~{totals.conditional}",
        f"    On demand:   ~{totals.on_demand}",
        "",
    ]
    for entry in file_entries(files):
        out.append(
            f"    {entry['mode']:<12} {entry['scope']:<13} "
            f"{entry['lines']:>5} lines  ~{entry['tokens']:>5} tokens  "
            f"{entry['path']}"
        )
        out.extend(f"        note: {note}" for note in entry["notes"])
    out += ["", memory_line]
    if unverified:
        out.append(f"  Unverified limits: {', '.join(unverified)}")
    out += ["", DIVIDER]

    docs = [f for f in findings if f.source.kind == "docs"]
    heuristic = [f for f in findings if f.source.kind == "heuristic"]
    out += _render_group("Backed by Anthropic docs", docs)
    out += _render_group("Heuristics (this tool's own judgement)", heuristic)

    out += [DIVIDER, "  Deductions:"]
    if not score.deductions:
        out.append("    none")
    for d in score.deductions:
        suffix = " (capped)" if d.capped else ""
        out.append(f"    {d.check_id}: {d.count} finding(s), -{d.points}{suffix}")
    out += [
        "",
        f"  Score: {score.value}/100 (starts at 100; only deductions apply)",
        "",
    ]
    out.append(RULE)
    return "\n".join(out)
