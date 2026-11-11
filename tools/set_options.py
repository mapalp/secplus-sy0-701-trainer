"""Replace the options (and optionally stem text) of exam-grade items in a bank/src module.

Usage inside another script:  set_options(path, {"xg-d1-01": [...new options, correct first...]})
"""
import re
from pathlib import Path


def set_options(path, new, stem_fixes=None):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    for qid, opts in new.items():
        start = s.index(f'dict(id="{qid}"')
        nxt = s.find("dict(id=", start + 10)
        end = nxt if nxt != -1 else len(s)
        block = s[start:end]
        m = re.search(r"\no=\[.*?\],(\s*\n)?\s*(n=\d+,\s*)?(?=w=)|\no=\[.*?\],\n", block, re.S)
        if not m:
            raise SystemExit(f"{qid}: options not found")
        lit = "\no=[" + ",\n   ".join(repr(o).replace("\\'", "'") if '"' in o else '"' + o + '"' for o in opts) + "],\n"
        block = block[: m.start()] + lit + block[m.end():]
        s = s[:start] + block + s[end:]
    for old, newtxt in (stem_fixes or []):
        assert s.count(old) == 1, old[:60]
        s = s.replace(old, newtxt)
    p.write_text(s, encoding="utf-8")
