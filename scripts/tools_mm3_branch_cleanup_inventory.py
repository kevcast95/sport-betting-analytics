#!/usr/bin/env python3
"""Genera inventario y clasificación para MM-3 branch cleanup (una vez + reproducible)."""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "scripts" / "outputs"


def _git(args: list[str]) -> str:
    r = subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return (r.stdout or "").strip()


def _tracked_set() -> set[str]:
    out = _git(["ls-files", "-z"])
    return {p for p in out.split("\0") if p}


def _check_ignore(path: str) -> bool:
    r = subprocess.run(
        ["git", "-C", str(REPO), "check-ignore", "-q", path],
        capture_output=True,
    )
    return r.returncode == 0


def main() -> None:
    tracked = _tracked_set()
    rows_inv: list[dict[str, str]] = []
    rows_cls: list[dict[str, str]] = []
    rows_git: list[dict[str, str]] = []

    paths = sorted(
        p
        for p in OUT.glob("mm3*")
        if p.is_file()
    ) + sorted(p for p in OUT.glob("branch_cleanup*") if p.is_file())

    for p in paths:
        rel = str(p.relative_to(REPO))
        st = _git(["status", "--short", rel])
        git_st = st[:2] if st else "??"
        is_tracked = rel in tracked
        tu = "tracked" if is_tracked else "untracked"
        sz = p.stat().st_size
        name = p.name

        cat = "REVIEW_MANUALLY"
        action = "REVIEW_MANUALLY"

        if rel.startswith("scripts/mm3_") and rel.endswith(".py"):
            cat, action = "CODE", "KEEP_AND_COMMIT"
        elif "branch_cleanup" in name:
            cat, action = "CLEANUP_META", "KEEP_AND_COMMIT"
        elif "/docs/" in rel:
            cat, action = "AUDIT", "KEEP_AND_COMMIT"
        elif sz >= 600_000 or name.endswith("_raw.json"):
            cat, action = "LARGE_OR_RAW", "DO_NOT_COMMIT"
        elif "rejection_detail" in name or "matching_attempt" in name:
            cat, action = "LARGE_DETAIL", "DO_NOT_COMMIT"
        elif name in (
            "mm3_1b_toa_p0_match_rows.csv",
            "mm3_1b_toa_p0_rejections.csv",
            "mm3_1b_toa_p0_market_board_rows.csv",
            "mm3_1d_best_match_rows.csv",
            "mm3_1d_improved_market_board_rows.csv",
            "mm3_1d_roi_safe_subset_v1.csv",
            "mm3_1d_roi_safe_subset_v1.json",
            "mm3_1c_roi_safe_subset_v0.csv",
            "mm3_1c_roi_safe_subset_v0.json",
            "mm3_1a_backfill_batches.json",
            "mm3_1a_toa_pilot_raw.json",
        ) or name.startswith("mm3_1e_roi_safe_subset_v2"):
            cat, action = "LARGE_ARTIFACT", "DO_NOT_COMMIT"
        elif name.endswith("_summary.json") or name.endswith("_readiness.json") or name.endswith("_decision.json"):
            cat, action = "SUMMARY", "KEEP_AND_COMMIT"
        elif name.endswith("_recommended_markets.json") or name.endswith("_cost.json"):
            cat, action = "SUMMARY", "KEEP_AND_COMMIT"
        elif sz <= 130_000 and (name.endswith(".json") or name.endswith(".csv")):
            cat, action = "SMALL_ARTIFACT", "KEEP_AND_COMMIT_OR_SUMMARY"
        elif name == "mm3_1a_big5_fixture_inventory.csv":
            cat, action = "PIPELINE_INPUT", "KEEP_AND_COMMIT"
        elif "checkpoint" in name:
            cat, action = "CHECKPOINT", "DO_NOT_COMMIT"
        else:
            cat, action = "MEDIUM_ARTIFACT", "KEEP_AS_DOC_SUMMARY_ONLY"

        if action == "KEEP_AND_COMMIT_OR_SUMMARY":
            action = "KEEP_AS_DOC_SUMMARY_ONLY" if sz > 50_000 else "KEEP_AND_COMMIT"

        rows_inv.append(
            {
                "path": rel,
                "git_status": git_st,
                "tracked_untracked": tu,
                "size_bytes": str(sz),
                "gitignored": str(_check_ignore(rel)),
                "category_guess": cat,
                "recommended_action": action,
            }
        )

        rows_cls.append(
            {
                "path": rel,
                "bucket": action,
                "category_guess": cat,
                "size_bytes": str(sz),
            }
        )

    # gitignore recommendations
    ign = [
        ("scripts/outputs/mm3_1b_toa_p0_match_rows.csv", "large_match_rows_reproducible_with_backfill"),
        ("scripts/outputs/mm3_1b_toa_p0_rejections.csv", "large_rejections"),
        ("scripts/outputs/mm3_1b_toa_p0_market_board_rows.csv", "large_board_rows"),
        ("scripts/outputs/mm3_1c_rejection_detail_rows.csv", "large_rejection_detail"),
        ("scripts/outputs/mm3_1c_kickoff_tolerance_candidates.csv", "large_tolerance_grid"),
        ("scripts/outputs/mm3_1d_matching_attempt_rows.csv", "large_attempt_grid"),
        ("scripts/outputs/mm3_1d_best_match_rows.csv", "large_best_match"),
        ("scripts/outputs/mm3_1d_improved_market_board_rows.csv", "large_improved_board_rows"),
        ("scripts/outputs/mm3_1d_roi_safe_subset_v1.csv", "large_roi_subset"),
        ("scripts/outputs/mm3_1d_roi_safe_subset_v1.json", "large_roi_subset_json"),
        ("scripts/outputs/mm3_1c_roi_safe_subset_v0.csv", "large_roi_subset"),
        ("scripts/outputs/mm3_1c_roi_safe_subset_v0.json", "large_roi_subset_json"),
        ("scripts/outputs/mm3_1e_roi_safe_subset_v2_full.csv", "large_roi_v2"),
        ("scripts/outputs/mm3_1e_roi_safe_subset_v2_stratified.csv", "large_roi_v2"),
        ("scripts/outputs/mm3_1e_roi_safe_subset_v2_weighted.csv", "large_roi_v2"),
        ("scripts/outputs/mm3_1a_backfill_batches.json", "large_batch_plan"),
        ("scripts/outputs/mm3_1a_toa_pilot_raw.json", "raw_pilot_payload"),
        (".pytest_cache/", "pytest_cache"),
        ("**/__pycache__/", "python_cache"),
    ]
    for pat, why in ign:
        rows_git.append({"pattern": pat, "reason": why, "apply": "append_if_missing"})

    _write(OUT / "branch_cleanup_inventory_before.csv", list(rows_inv[0].keys()), rows_inv)
    _write(OUT / "branch_cleanup_file_classification.csv", list(rows_cls[0].keys()), rows_cls)
    _write(OUT / "branch_cleanup_gitignore_recommendations.csv", list(rows_git[0].keys()), rows_git)
    print(f"OK: {len(rows_inv)} paths inventoried", file=sys.stderr)


def _write(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})


if __name__ == "__main__":
    main()
