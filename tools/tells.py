"""Print exam-grade items that still carry a length tell or word cue, with option lengths.

Usage: python3 tools/tells.py [id-prefix]     e.g. python3 tools/tells.py xg-d2  or  b-pki
"""
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tells = runpy.run_path(str(ROOT / "tools" / "audit.py"), run_name="audit_lib")["tells"]
prefix = sys.argv[1] if len(sys.argv) > 1 else "xg-"
banks = ["exam_grade.json", "baseline_builder.json", "exam2_misses.json", "stubborn_pile.json"]
items = [q for b in banks for q in json.loads((ROOT / "bank" / b).read_text()) if str(q["id"]).startswith(prefix)]
n_long = 0
for q in items:
    lg, cue = tells(q)
    n_long += lg
    if lg or cue:
        n = q.get("n", 1)
        print(f"{q['id']}  {'LONGEST ' if lg else ''}{'CUE ' + ','.join(cue) if cue else ''}")
        for i, o in enumerate(q["o"]):
            print(f"   {'*' if i < n else ' '}{len(o):3d}  {o}")
singles = sum(q.get("n", 1) == 1 for q in items)
print(f"\n{prefix}: correct answer longest in {n_long}/{singles} single-answer items ({n_long / max(1, singles):.0%})")
