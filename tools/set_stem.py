"""Replace the stem (q=...) of exam-grade items in a bank/src module.  set_stem(path, {id: new_stem})"""
import re
from pathlib import Path


def set_stem(path, new):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for qid, stem in new.items():
        start = s.index(f'dict(id="{qid}"')
        m = re.compile(r'\nq="(?:[^"\\]|\\.)*",\n').search(s, start)
        if not m or s.find("dict(id=", start + 10) not in (-1,) and m.start() > s.find("dict(id=", start + 10):
            raise SystemExit(f"{qid}: stem not found")
        s = s[: m.start()] + "\nq=" + '"' + stem.replace('"', '\\"') + '",\n' + s[m.end():]
    p.write_text(s, encoding="utf-8")
