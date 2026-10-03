#!/usr/bin/env python3
"""Analyse the CLAUDE.md files Claude Code loads and report findings and a score."""

import json
import os
import sys
from pathlib import Path

import claude_md.checks  # noqa: F401
from claude_md import limits
from claude_md.discovery import default_managed_dir, discover, memory_dir
from claude_md.findings import Context, run_checks
from claude_md.model import totals
from claude_md.report import render, to_json_data
from claude_md.scoring import score


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--json"]
    project_dir = Path(args[0] if args else os.getcwd()).resolve()
    home_dir = Path.home()

    files = discover(project_dir, home_dir, default_managed_dir())
    found = run_checks(files, Context(project_dir, home_dir))
    result = score(found)
    context_totals = totals(files)
    unverified = limits.unverified_limit_names()
    memory_path = memory_dir(project_dir, home_dir)
    memory_found = memory_path.is_dir()

    if "--json" in sys.argv:
        data = to_json_data(
            files,
            context_totals,
            found,
            result,
            unverified,
            memory_path,
            memory_found,
        )
        print(json.dumps(data, indent=2))
        return
    print(
        render(
            files,
            context_totals,
            found,
            result,
            unverified,
            project_dir,
            memory_path,
            memory_found,
        )
    )


if __name__ == "__main__":
    main()
