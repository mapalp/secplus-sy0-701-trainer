# SY0-701 Drill and Exam Tool

A single-file CompTIA Security+ (SY0-701) practice tool: quick drill rounds that track every answer, plus timed full and half practice exams with performance-based questions (PBQs).

It's an unofficial study aid and isn't affiliated with CompTIA. All questions are original.

## Use it

Open one of the built files in a browser. Nothing needs to be installed.

| File | Saves progress to |
| --- | --- |
| `dist/sy0-701-trainer.html` | Your claude.ai account when hosted as a Claude artifact; otherwise this browser |
| `dist/sy0-701-trainer-offline.html` | This browser only (use **Export progress file** to move it) |

Your progress and results never go into this repository. They stay in your browser or your claude.ai account. Exported exam reports (Markdown) and progress files belong in a local `results/` folder, which `.gitignore` excludes.

## Question banks

| Bank | Items | Used in |
| --- | --- | --- |
| Exam grade | 253 multiple choice + 12 multi-part PBQs | Hard exams (only source), standard exams, drills if selected |
| Exam 2 misses | 45 | Drills, standard exams |
| Stubborn pile | 60 | Drills, standard exams |
| Baseline builder | 616 | Drills only |
| Legacy PBQs | 24 | Standard exams, PBQ drills |
| New angles | generated | Written per user in the hosted version; stored in the artifact database |

Every bank is held to the same exam-grade standard (rewritten November 2026). The **Exam grade** bank is the one written fresh for it:

- Most stems are 2-5 sentence scenarios with constraints and a detail that doesn't matter.
- Distractors are real SY0-701 terms from the same family as the answer.
- Some questions are multi-select.
- Some questions include logs, configs, or rule sets.
- The PBQs are multi-part, and their choice lists are longer than their rows, so they can't be solved by elimination.

**Hard mode** draws only from this bank and gives 75 minutes for 90 items. Drills hold these questions back by default so they stay unseen for exams.

`reports/audit.md` measures every bank: stem length, exhibits, qualifier wording, how often the correct answer is the longest option, word cues, and multi-select count. `reports/item_audit.md` grades each item PASS / FIX / REWRITE against the standard (scenario stem of 25+ words or an exhibit, no throwaway options, no word cues, correct answer longest in 25% or fewer of a bank's items) and checks every PBQ.

## Repository layout

```
src/engine.html          the app, with /*@@BANKS@@*/ and /*@@MODE@@*/ placeholders
bank/*.json              question banks (exam_grade.json is generated from bank/src)
bank/src/*.py            exam-grade questions, one file per domain (MC and PBQ lists)
bank/src_legacy/*.py     rewrites of the older banks; each item replaces the JSON item with the same id
tools/build.py           compiles bank/src, then writes dist/ (online and offline builds)
tools/audit.py           validates the exam-grade bank and writes reports/audit.md
tools/audit_items.py     grades every item in every bank and writes reports/item_audit.md
tools/tells.py           lists items whose answer gives itself away, with option lengths
tools/set_options.py     helper for rewriting an item's options (set_stem.py does the same for stems)
dist/                    built single-file apps
```

## Build

```bash
python3 tools/build.py && python3 tools/audit.py && python3 tools/audit_items.py
```

Python 3.9 or later, standard library only. `tools/extract_from_artifact.py` was a one-time import and also needs the `json5` package.

### Question format

```python
dict(id="xg-d1-01", t="Cryptography",          # t must be a topic listed in TOPIC_DOMAIN in src/engine.html
     q="Scenario stem...",
     c="optional exhibit: log, config, or rule set",
     o=["correct answer", "distractor", "distractor", "distractor"],   # correct first; the app shuffles
     n=2,                                         # optional: first n options are correct (multi-select)
     w="Why the answer wins and why each distractor loses.",
     h="Short memory hook.")
```
