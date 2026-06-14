#!/usr/bin/env python3
"""Score all lessons for quality and compute contributor quality metrics.

Output:
  - stdout: per-lesson score breakdown
  - data/quality_scores.json: machine-readable report
  - contributor quality stats for frontend leaderboard

Scoring dimensions (each 0-2, total 0-10):
  - Frontmatter completeness: has title, domain, tags, status
  - Structure: has problem section (背景/Root Cause) + solution section (方案/Solution)
  - Content depth: body length + code block presence
  - Maintenance: has created + updated timestamps
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = REPO_ROOT / "lessons"
TASKS_DIR = REPO_ROOT / "tasks"
OUTPUT_PATH = REPO_ROOT / "data" / "quality_scores.json"
DRY_RUN = "--dry-run" in sys.argv
VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv

# Required sections in body
PROBLEM_HEADINGS = re.compile(r"^##\s+(背景|问题|Root Cause|Problem|Issue|Motivation)", re.MULTILINE | re.IGNORECASE)
SOLUTION_HEADINGS = re.compile(r"^##\s+(方案|Solution|Fix|修复|Implementation|Approach)", re.MULTILINE | re.IGNORECASE)
VERIFY_HEADINGS = re.compile(r"^##\s+(验证|验证方式|Verify|验证结果|Result|效果|Impact)", re.MULTILINE | re.IGNORECASE)


def score_frontmatter(fm: dict | None) -> tuple[int, list[str]]:
    """0-2 points for frontmatter completeness"""
    scores = []
    notes = []
    if not fm:
        return 0, ["No frontmatter (0/2)"]

    required = ["title", "domain", "status"]
    hits = sum(1 for r in required if fm.get(r))
    tags = fm.get("tags", [])
    if hits == 3 and len(tags) >= 2:
        scores.append(2)
        notes.append("Complete + tags")
    elif hits >= 2:
        scores.append(1)
        notes.append("Partial frontmatter")
    else:
        scores.append(0)
        notes.append("Missing metadata")

    return sum(scores), notes


def score_structure(body: str) -> tuple[int, list[str]]:
    """0-2 points for body structure"""
    notes = []
    has_problem = bool(PROBLEM_HEADINGS.search(body))
    has_solution = bool(SOLUTION_HEADINGS.search(body))
    has_verify = bool(VERIFY_HEADINGS.search(body))

    if has_problem and has_solution and has_verify:
        notes.append("Full 3-part structure")
        return 2, notes
    elif has_problem and has_solution:
        notes.append("Problem + Solution (no Verify)")
        return 1, notes
    elif has_problem or has_solution:
        notes.append("Only one section found")
        return 1, notes
    notes.append("No recognizable structure")
    return 0, notes


def score_content(body: str) -> tuple[int, list[str]]:
    """0-2 points for content depth"""
    notes = []
    text_only = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    text_only = re.sub(r"\s+", " ", text_only).strip()
    char_count = len(text_only)
    has_code = bool(re.search(r"```", body))
    has_list = bool(re.search(r"^\s*[-*]\s+", body, re.MULTILINE))

    points = 0
    if char_count > 500:
        points += 1
        notes.append(f"Body {char_count} chars")
    if has_code:
        points += 1
        notes.append("Code blocks present")
    if not has_code and has_list:
        points += 0.5
        notes.append("List formatting")

    return min(points, 2), notes


def score_maintenance(fm: dict | None) -> tuple[int, list[str]]:
    """0-2 points for maintenance metadata"""
    notes = []
    if not fm:
        return 0, ["No metadata"]

    has_created = bool(fm.get("created"))
    has_updated = bool(fm.get("updated"))
    source = fm.get("source", "")

    points = 0
    if has_created and has_updated:
        points += 1
        notes.append("Timestamps")
    if source:
        points += 1
        notes.append(f"Source: {source[:20]}")

    return min(points, 2), notes


def score_extra(body: str, fm: dict | None) -> tuple[int, list[str]]:
    """0-2 bonus points for extra polish"""
    notes = []
    points = 0

    # Has actionable content (commands, configs)
    code_blocks = re.findall(r"```(\w+)?\n(.*?)```", body, re.DOTALL)
    actionable_cmds = sum(1 for lang, code in code_blocks
                          if not lang or lang in ("bash", "sh", "yaml", "json", "python"))
    if actionable_cmds >= 2:
        points += 1
        notes.append(f"Actionable: {actionable_cmds} blocks")

    # Has tags >= 3
    tags = (fm or {}).get("tags", [])
    if len(tags) >= 3:
        points += 1
        notes.append(f"{len(tags)} tags")

    # No placeholder text
    body_lower = body.lower()
    for placeholder in ["todo", "fixme", "coming soon"]:
        if placeholder in body_lower:
            points -= 0.5
            notes.append(f"Has '{placeholder}' placeholder")

    return max(points, 0), notes


def score_lesson(path: Path) -> dict:
    """Score a single lesson file."""
    content = path.read_text(encoding="utf-8")

    # Extract frontmatter
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    fm = None
    if m:
        try:
            fm = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Body (strip frontmatter)
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, count=1, flags=re.DOTALL)

    dims = {
        "frontmatter": score_frontmatter(fm),
        "structure": score_structure(body),
        "content": score_content(body),
        "maintenance": score_maintenance(fm),
        "extra": score_extra(body, fm),
    }

    total = sum(d[0] for d in dims.values())
    all_notes = []
    for dim_name, (score, notes) in dims.items():
        if notes:
            all_notes.extend(notes)

    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "title": (fm or {}).get("title", path.stem),
        "domain": (fm or {}).get("domain", "unknown"),
        "score": round(total, 1),
        "dimensions": {k: round(v[0], 1) for k, v in dims.items()},
        "notes": all_notes,
        "source": (fm or {}).get("source", ""),
        "status": (fm or {}).get("status", ""),
    }


def main():
    paths = sorted(LESSONS_DIR.rglob("*.md"))
    results = []

    total_score = 0
    max_score = 0

    for path in paths:
        if path.name in ("index.md", "README.md"):
            continue
        if "_archive" in str(path):
            continue

        result = score_lesson(path)
        results.append(result)
        total_score += result["score"]
        max_score += 10

        if VERBOSE:
            dims = " ".join(f"{k}={v}" for k, v in result["dimensions"].items())
            notes = "; ".join(result["notes"][:3])
            print(f"  {result['score']:4.1f}  {result['title'][:40]:40s}  [{dims}]")

    # Sort by score descending
    results.sort(key=lambda x: -x["score"])

    # Summary
    avg = total_score / len(results) if results else 0
    print(f"\n{'='*50}")
    print(f"Total lessons scored: {len(results)}")
    print(f"Average score:        {avg:.1f}/10")
    print(f"Median lesson:        {results[len(results)//2]['score']:.1f}/10")
    print(f"Top scorer:           {results[0]['title']} ({results[0]['score']}/10)")
    print(f"Bottom scorer:        {results[-1]['title']} ({results[-1]['score']}/10)")
    print(f"Score ≥ 7:            {sum(1 for r in results if r['score'] >= 7)} lessons")
    print(f"Score ≤ 3:            {sum(1 for r in results if r['score'] <= 3)} lessons")

    # Save report
    if not DRY_RUN:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "summary": {
                "total": len(results),
                "average": round(avg, 2),
                "median": results[len(results)//2]["score"],
                "top": results[0]["title"],
                "bottom": results[-1]["title"],
            },
            "scores": results,
        }
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nSaved: {OUTPUT_PATH}")

    # Contributor quality aggregation
    contrib_quality = {}
    for r in results:
        source = r.get("source", "") or "core"
        if source not in contrib_quality:
            contrib_quality[source] = {"count": 0, "total_score": 0.0, "lessons": []}
        contrib_quality[source]["count"] += 1
        contrib_quality[source]["total_score"] += r["score"]
        contrib_quality[source]["lessons"].append(r["title"])

    print(f"\n{'='*50}")
    print("Contributor quality (by source):")
    for src, data in sorted(contrib_quality.items(), key=lambda x: -x[1]["total_score"]):
        avg_src = data["total_score"] / data["count"]
        print(f"  {src:20s}  {data['count']:3d} lessons  avg {avg_src:.1f}/10")


if __name__ == "__main__":
    main()
