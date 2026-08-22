# _meta — constitution, ledgers, and operational state

`CLAUDE.md` (repo root) is the constitutional document — hard rules, gates, live-strategy snapshot,
lesson registry summary. Files here are split out of it (2026-07-30, to stay under the Claude Code
context-size limit) or hold state that changes between sessions. Read `CLAUDE.md` first; come here
for the full text or the operational detail it points to.

## Contents

| File | What it holds |
|---|---|
| `lessons_registry.md` | The full text of lessons L11-L60 — the compressed cross-study record. `CLAUDE.md` cites these by number; this file has the verbatim entries |
| `l_aliases.md` | Table mapping historical in-report names ("L33 candidate", "L34 (proposé)") to the lesson number they were later reconciled to. Artifacts are never rewritten, so a report can cite an alias — check this table before assuming a cited "L-number" that doesn't match the registry is an error |
| `n_tests_ledger.md` | The multiple-testing counter convention: a frozen global count (321, fixed 2026-05-30) plus a per-programme local counter for everything tested since, reconciled at each programme's close. Sub-totals overlap and are never summed; only the sequential milestones are additive |
| `data_governance.md` | What belongs in `data/` vs a research folder, what gets gitignored, what a subset needs before it can be deleted |
| `research_active.md` | Index of currently open research programmes: paths, sample sizes, one-line status |
| `reconciliation_2026-06-10.md` | Record of the 2026-06-10 cleanup/reconciliation pass (paths consolidated, counters reconciled) |
| `current_focus.md` | Session-level operational state — immediate blockers, in-progress work. Meant to be updated every session; check the "last updated" date against today before trusting it |
| `TODO.md` | Prioritized task list with owner, effort, and completion criterion per entry |
| `open_questions.md` | Unresolved infra/attribution questions that didn't get closed out at the time they were found |

## Convention

Numbers are graved (assigned a permanent lesson number) only at session close, in this directory —
never inside a session ("no number minting inside a session", per `CLAUDE.md` §Parallel session
coordination). A session can name a candidate lesson; only a reconciliation pass here turns it into
an L-number.

## Integrity check

`tools/check_register_integrity.py` verifies that every path cited in the lesson registry and
related documents still exists and is git-tracked, and that the n_tests chain is monotonic. Run it
in the **main working directory**, never inside a worktree — a worktree lacks the local/gitignored
artifacts some entries cite, which would otherwise report as false `MISSING`.
