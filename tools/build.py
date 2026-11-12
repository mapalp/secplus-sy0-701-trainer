"""Assemble the single-file trainer from the engine template and the JSON question banks.

Usage:  python3 tools/build.py
Writes: dist/sy0-701-trainer.html          (online: saves to your claude.ai account when hosted as an artifact,
                                             otherwise to this browser)
        dist/sy0-701-trainer-offline.html  (offline: saves to this browser only; export to sync)

No personal data is ever written into the output: the offline build carries an EMPTY seed.
"""
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "bank"
DIST = ROOT / "dist"

# The offline copy keys its browser storage on this timestamp. Keep it fixed so an existing
# offline history (saved under secplus-drill-lab-v1-offline-20261108120000) is still found.
OFFLINE_SEED_AT = "2026-11-08T12:00:00Z"


def load(name):
    return json.loads((BANK / name).read_text(encoding="utf-8"))


def compile_exam_grade():
    """Exam-grade items are authored as Python modules in bank/src (easier to write and review);
    compile them into bank/exam_grade.json and bank/pbq_exam_grade.json."""
    mc, pbq = [], []
    for f in sorted((BANK / "src").glob("*.py")):
        mod = runpy.run_path(str(f))
        mc += mod.get("MC", [])
        pbq += mod.get("PBQ", [])
    for p in pbq:
        p["xg"] = True
    (BANK / "exam_grade.json").write_text(json.dumps(mc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (BANK / "pbq_exam_grade.json").write_text(json.dumps(pbq, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return mc, pbq


def apply_legacy_rewrites():
    """Rewrites of the older banks live in bank/src_legacy/*.py. Each module sets BANK (the JSON file's stem)
    and MC and/or PBQ lists; every item replaces the existing item with the same id, so answer history carries over."""
    by_bank = {}
    for f in sorted((BANK / "src_legacy").glob("*.py")):
        mod = runpy.run_path(str(f))
        b = by_bank.setdefault(mod["BANK"], {})
        for item in mod.get("MC", []) + mod.get("PBQ", []):
            if item["id"] in b:
                raise SystemExit(f"{f.name}: id {item['id']} rewritten twice")
            b[item["id"]] = item
    for bank, items in by_bank.items():
        path = BANK / f"{bank}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        index = {str(x["id"]): i for i, x in enumerate(data)}
        for qid, item in items.items():
            if str(qid) not in index:
                raise SystemExit(f"{bank}: rewrite for unknown id {qid}")
            old = data[index[str(qid)]]
            if old.get("t") != item.get("t"):
                raise SystemExit(f"{bank} {qid}: topic changed from {old.get('t')} to {item.get('t')}")
            data[index[str(qid)]] = {**item, "id": old["id"]}   # keep the original id type (int or str)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{bank}: {len(items)} rewritten items applied")


def js(obj):
    # "</" inside a string would end the <script> element early
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main():
    apply_legacy_rewrites()
    xg_mc, xg_pbq = compile_exam_grade()
    banks = (
        f"const BANK_E2={js(load('exam2_misses.json'))};\n"
        f"const BANK_SP={js(load('stubborn_pile.json'))};\n"
        f"const PBQ_BANK={js(load('pbq_legacy.json') + xg_pbq)};\n"
        f"const BANK_BB={js(load('baseline_builder.json'))};\n"
        f"const BANK_XG={js(xg_mc)};"
    )
    engine = (ROOT / "src" / "engine.html").read_text(encoding="utf-8")
    assert engine.count("/*@@BANKS@@*/") == 1 and engine.count("/*@@MODE@@*/") == 1
    DIST.mkdir(exist_ok=True)
    seed = {"at": OFFLINE_SEED_AT, "stats": {}, "sessions": [], "gen": []}
    variants = {
        "sy0-701-trainer.html": ("const OFFLINE=false;const SEED=null;", None),
        "sy0-701-trainer-offline.html": (f"const OFFLINE=true;const SEED={js(seed)};",
                                         ("<title>SY0-701 Drill and Exam Tool</title>", "<title>SY0-701 Drill and Exam Tool (offline)</title>")),
    }
    for name, (mode, title) in variants.items():
        html = engine.replace("/*@@BANKS@@*/", banks).replace("/*@@MODE@@*/", mode)
        if title:
            assert html.count(title[0]) == 1
            html = html.replace(*title)
        (DIST / name).write_text(html, encoding="utf-8")
        print(f"dist/{name}: {len(html) / 1024:.0f} KB")
    print(f"exam grade: {len(xg_mc)} multiple choice, {len(xg_pbq)} PBQs")


if __name__ == "__main__":
    main()
