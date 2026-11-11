"""One-time: split the live artifact HTML into an engine template plus JSON question banks.

Usage: python tools/extract_from_artifact.py src/live_artifact.html
Writes src/engine.html and bank/*.json.
"""
import json
import re
import sys
from pathlib import Path

import json5  # parses the JS object literals used by the older banks

ROOT = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1]).read_text(encoding="utf-8")
lines = src.split("\n")


def find(prefix):
    for i, l in enumerate(lines):
        if l.startswith(prefix):
            return i
    raise SystemExit(f"not found: {prefix}")


i_e2, i_sp, i_mode, i_pbq, i_bb = (find(p) for p in ("const BANK_E2", "const BANK_SP", "const OFFLINE", "const PBQ_BANK", "const BANK_BB"))
assert i_e2 < i_sp < i_mode < i_pbq < i_bb


def js_array(text):
    body = text[text.index("[") : text.rindex("]") + 1]
    return json5.loads(body)


banks = {
    "exam2_misses.json": js_array("\n".join(lines[i_e2:i_sp])),
    "stubborn_pile.json": js_array("\n".join(lines[i_sp:i_mode])),
    "pbq_legacy.json": json.loads(lines[i_pbq][lines[i_pbq].index("[") : lines[i_pbq].rindex("]") + 1]),
    "baseline_builder.json": json.loads(lines[i_bb][lines[i_bb].index("[") : lines[i_bb].rindex("]") + 1]),
}
for name, data in banks.items():
    (ROOT / "bank" / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{name}: {len(data)}")

engine = lines[:i_e2] + ["/*@@BANKS@@*/"] + lines[i_bb + 1 :]
text = "\n".join(engine)
# the mode line sits inside the removed block; re-insert it as its own marker right after the banks
text = text.replace("/*@@BANKS@@*/", "/*@@BANKS@@*/\n/*@@MODE@@*/", 1)
(ROOT / "src" / "engine.html").write_text(text, encoding="utf-8")
print("engine.html lines:", text.count("\n") + 1)
