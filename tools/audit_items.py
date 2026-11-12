"""Score every question in every bank against the exam-grade standard, item by item.

Usage:  python3 tools/audit_items.py [extra_bank.json ...]
Writes: reports/item_audit.md (summary + per-item verdicts)

Verdicts
  PASS     meets the standard
  FIX      scenario is strong enough, but the options give the answer away (length or word cue)
  REWRITE  stem is a definition or one-liner, or a distractor is a throwaway
"""
import json
import re
import runpy
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
lib = runpy.run_path(str(ROOT / "tools" / "audit.py"), run_name="audit_lib")
tells, TOPIC_DOMAIN = lib["tells"], lib["TOPIC_DOMAIN"]

# Options nobody who studied would pick: they let a test-taker eliminate by common sense alone.
THROWAWAY = re.compile(
    r"\b(say nothing|do nothing|wait (to see|and see)|ignore (it|the|both)|leave backdoors?|delete the client's logs|"
    r"turn off (overnight )?logging|disable (all )?logging|switch .*to WEP|open (tcp )?3389 to the internet|"
    r"longer usernames?|hiding the login page|slower wi-?fi|a new printer|email (them|it) a sample|"
    r"copy production data as-is|give developers production access|forward it to coworkers|"
    r"keep copies of client data|shared admin account|wrong ssid|delete older alerts|"
    r"spike in help desk tickets|failing backup job|dns (outage|misconfiguration)$)", re.I)
DEFINITION = re.compile(
    r"^(what is|what are|which (term|type|law|team|standard|policy|device|principle|agreement|tool|protocol|port|algorithm)"
    r"|what (type|term|kind)|under gdpr, (what|which)|who is|what does .{1,40} stand for)", re.I)


def sentences(s):
    return len(re.findall(r"[.?!](\s|$)", s))


def verdict(q):
    reasons = []
    words = len(q["q"].split())
    if words < 25 and not q.get("c"):
        reasons.append(f"short stem ({words} words)")
    if sentences(q["q"]) < 2 and not q.get("c"):
        reasons.append("no scenario")
    if DEFINITION.search(q["q"].strip()):
        reasons.append("definition question")
    junk = [o for o in q["o"][q.get("n", 1):] if THROWAWAY.search(o)]
    if junk:
        reasons.append("throwaway option: " + "; ".join(junk))
    longest, cue = tells(q)
    # A longest correct answer is only a problem at bank level (over 25% of items), so it is reported per bank below.
    fix = []
    if cue:
        fix.append("word cue: " + ", ".join(cue))
    if reasons:
        return "REWRITE", reasons + fix
    if fix:
        return "FIX", fix
    return "PASS", []


def main():
    banks = {
        "Exam grade": json.loads((ROOT / "bank" / "exam_grade.json").read_text()),
        "Exam 2 misses": json.loads((ROOT / "bank" / "exam2_misses.json").read_text()),
        "Stubborn pile": json.loads((ROOT / "bank" / "stubborn_pile.json").read_text()),
        "Baseline builder": json.loads((ROOT / "bank" / "baseline_builder.json").read_text()),
    }
    for extra in sys.argv[1:]:
        banks[Path(extra).stem] = json.loads(Path(extra).read_text())

    L = ["# Item-level audit against the exam-grade standard", "",
         "| Bank | Items | PASS | FIX (word cue) | REWRITE | Correct answer longest (bank, target 25% or less) | Main problems |", "| --- | --- | --- | --- | --- | --- | --- |"]
    detail = []
    for name, items in banks.items():
        c, why = Counter(), Counter()
        rows = []
        for q in items:
            v, r = verdict(q)
            c[v] += 1
            for x in r:
                why[re.sub(r"\(.*|:.*", "", x).strip()] += 1
            if v != "PASS":
                rows.append(f"| {q['id']} | {q['t']} | {v} | {'; '.join(r)[:160]} |")
        singles = [q for q in items if q.get("n", 1) == 1]
        rate = sum(tells(q)[0] for q in singles) / max(1, len(singles))
        top = ", ".join(f"{k} {n}" for k, n in why.most_common(4))
        L.append(f"| {name} | {len(items)} | {c['PASS']} | {c['FIX']} | {c['REWRITE']} | {rate:.0%} | {top} |")
        if rows:
            detail += ["", f"## {name}", "", "| ID | Topic | Verdict | Reasons |", "| --- | --- | --- | --- |"] + rows

    pbqs = json.loads((ROOT / "bank" / "pbq_legacy.json").read_text())
    L += ["", "## Legacy PBQs", "", "| ID | Type | Rows | Choices | Prompt words | Exhibit | Verdict |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for p in pbqs:
        rows = p.get("rows") or p.get("items") or []
        ch = p.get("choices") or p.get("actions") or []
        shared_users = [r for r in rows if isinstance(r, dict) and not r.get("choices")] if p["type"] == "match" else []
        one_to_one = p["type"] == "match" and ch and len(shared_users) >= len(ch) and len({r["a"] for r in shared_users}) == len(shared_users)
        words = len(p.get("prompt", "").split())
        problems = []
        if one_to_one:
            problems.append("one-to-one matching")
        if words < 25 and not p.get("exhibit"):
            problems.append("thin prompt, no exhibit")
        v = "REWRITE" if problems else "PASS"
        L.append(f"| {p['id']} | {p['type']} | {len(rows)} | {len(ch)} | {words} | {'yes' if p.get('exhibit') else 'no'} | {v}{': ' + ', '.join(problems) if problems else ''} |")

    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "item_audit.md").write_text("\n".join(L + detail) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
