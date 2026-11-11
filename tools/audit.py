"""Audit every question bank for the tells that make practice questions easier than the real exam,
and validate the exam-grade bank strictly.

Usage:  python3 tools/audit.py        (run tools/build.py first so bank/exam_grade.json is current)
Writes: reports/audit.md   Exit code 1 if any exam-grade item fails validation.
"""
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "bank"

engine = (ROOT / "src" / "engine.html").read_text(encoding="utf-8")
td_src = re.search(r"const TOPIC_DOMAIN=\{(.*?)\};", engine, re.S).group(1)
TOPIC_DOMAIN = {k: int(v) for k, v in re.findall(r'"([^"]+)":(\d)', td_src)}

STOP = set("""which their there about would should could these those other after before while where being using
within without because still since every first them they then than this that with from have what when your into
most best only more also does will were been each must make made over such some same following below shows
company employee employees users user security system systems team analyst administrator control controls attack attacks""".split())
QUAL = re.compile(r"\b(BEST|MOST|FIRST|NEXT|PRIMARY|LEAST|NOT|FAIL|EXCEPT)\b")


def words(s):
    return {w for w in re.findall(r"[a-z][a-z0-9\-']{4,}", s.lower()) if w not in STOP}


def tells(q):
    """(correct answer is strictly longest, word-cue list). Items with an 'ack' note were reviewed and accepted."""
    if q.get("ack"):
        return False, []
    n = q.get("n", 1)
    right, wrong = q["o"][:n], q["o"][n:]
    longest = n == 1 and len(right[0]) > max(len(o) for o in wrong)
    stem = words(q["q"] + " " + (q.get("c") or ""))
    others = set().union(*(words(o) for o in wrong))
    cue = sorted(w for w in stem & set().union(*(words(o) for o in right)) if w not in others)
    return longest, cue


def metrics(items):
    if not items:
        return None
    wc = [len(q["q"].split()) for q in items]
    sent = sum(len(re.findall(r"[.?!](\s|$)", q["q"])) >= 3 for q in items)
    t = [tells(q) for q in items]
    singles = [q for q in items if q.get("n", 1) == 1]
    return {
        "n": len(items),
        "median_words": statistics.median(wc),
        "under_15_words": f"{sum(w <= 15 for w in wc) / len(items):.0%}",
        "three_plus_sentences": f"{sent / len(items):.0%}",
        "exhibit": f"{sum(bool(q.get('c')) for q in items) / len(items):.0%}",
        "qualifier": f"{sum(bool(QUAL.search(q['q'])) for q in items) / len(items):.0%}",
        "correct_longest": f"{sum(x[0] for x in t) / max(1, len(singles)):.0%}",
        "word_cue": f"{sum(bool(x[1]) for x in t) / len(items):.0%}",
        "multi_select": sum(q.get("n", 1) > 1 for q in items),
    }


def validate(mc, pbq, all_ids):
    errs = []
    for q in mc:
        i = q.get("id", "?")
        for k in ("id", "t", "q", "o", "w", "h"):
            if not q.get(k):
                errs.append(f"{i}: missing {k}")
        if q.get("t") not in TOPIC_DOMAIN:
            errs.append(f"{i}: topic '{q.get('t')}' is not mapped to a domain")
        n = q.get("n", 1)
        if len(q.get("o", [])) < 4 or len(set(q.get("o", []))) != len(q.get("o", [])):
            errs.append(f"{i}: needs 4+ distinct options")
        if n > 1 and len(q["o"]) < n + 3:
            errs.append(f"{i}: choose-{n} needs at least {n + 3} options")
        if all_ids[i] > 1:
            errs.append(f"{i}: duplicate id")
    for p in pbq:
        i = p.get("id", "?")
        if p.get("t") not in TOPIC_DOMAIN:
            errs.append(f"{i}: topic not mapped")
        if p["type"] == "match":
            for r in p["rows"]:
                ch = r.get("choices") or p.get("choices") or []
                if r["a"] not in ch:
                    errs.append(f"{i}: answer '{r['a']}' not in its choices")
            shared = p.get("choices") or []
            users = [r for r in p["rows"] if not r.get("choices")]
            # one-to-one matching (every answer distinct, as many rows as choices) can be solved by elimination
            if shared and len(users) >= len(shared) and len({r["a"] for r in users}) == len(users):
                errs.append(f"{i}: shared choice list is not longer than the rows that use it (solvable by elimination)")
        if all_ids[i] > 1:
            errs.append(f"{i}: duplicate id")
    return errs


def main():
    banks = {
        "Exam grade": json.loads((BANK / "exam_grade.json").read_text()),
        "Exam 2 misses": json.loads((BANK / "exam2_misses.json").read_text()),
        "Stubborn pile": json.loads((BANK / "stubborn_pile.json").read_text()),
        "Baseline builder": json.loads((BANK / "baseline_builder.json").read_text()),
    }
    xg_pbq = json.loads((BANK / "pbq_exam_grade.json").read_text())
    legacy_pbq = json.loads((BANK / "pbq_legacy.json").read_text())
    all_ids = Counter(str(q["id"]) for b in banks.values() for q in b)
    all_ids.update(p["id"] for p in xg_pbq + legacy_pbq)
    errs = validate(banks["Exam grade"], xg_pbq, all_ids)

    xg = banks["Exam grade"]
    dom = Counter(TOPIC_DOMAIN.get(q["t"]) for q in xg)
    pdom = Counter(TOPIC_DOMAIN.get(p["t"]) for p in xg_pbq)
    L = ["# Question bank audit", ""]
    L += ["## Difficulty markers by bank", "",
          "| Bank | Items | Median stem words | Stems of 15 words or fewer | 3+ sentences | Exhibit | BEST/MOST/FIRST wording | Correct answer longest | Word cue | Multi-select |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, items in banks.items():
        m = metrics(items)
        if m:
            L.append(f"| {name} | {m['n']} | {m['median_words']} | {m['under_15_words']} | {m['three_plus_sentences']} | {m['exhibit']} | {m['qualifier']} | {m['correct_longest']} | {m['word_cue']} | {m['multi_select']} |")
    L += ["", "Exam-grade targets: median stem 40+ words, 15-word stems near 0%, exhibits 25%+, correct-answer-longest 25% or less, word cues 0%, some multi-select.", ""]
    L += ["## Exam-grade coverage", "",
          "| Domain | Multiple choice | PBQs | Needed for 3 fresh hard exams (MC) |", "| --- | --- | --- | --- |"]
    need = {1: 30, 2: 57, 3: 45, 4: 69, 5: 51}
    for d in range(1, 6):
        L.append(f"| {d} | {dom.get(d, 0)} | {pdom.get(d, 0)} | {need[d]} |")
    L += ["", "## Exam-grade items with tells", ""]
    flagged = [(q["id"], *tells(q)) for q in xg]
    flagged = [f for f in flagged if f[1] or f[2]]
    L += [f"- {i}: {'correct answer is longest' if lg else ''}{'; ' if lg and cue else ''}{'word cue: ' + ', '.join(cue) if cue else ''}" for i, lg, cue in flagged] or ["- None."]
    acks = [q for q in xg if q.get("ack")]
    L += ["", "## Reviewed and accepted", ""] + ([f"- {q['id']}: {q['ack']}" for q in acks] or ["- None."])
    L += ["", "## Validation errors", ""] + ([f"- {e}" for e in errs] or ["- None."])
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12]))
    print(f"exam grade: {len(xg)} MC by domain {dict(sorted(dom.items()))}, {len(xg_pbq)} PBQs; tells on {len(flagged)} items; {len(errs)} validation errors")
    for e in errs[:20]:
        print("  ERROR", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
