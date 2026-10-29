# research-archive

The complete working repository of a solo systematic-trading research programme, April to
October 2026, published as is: every study, every pre-registration, every verdict, the lesson
registry, the live-system code, the session notes, in the order they were written. **Start with
[proof-of-edge](https://github.com/Guillaume-Beaudouin-Git/proof-of-edge)**, the curated
entry point; this repository exists so that anything cited there can be checked at its source,
with its commit date.

## What was changed before publication

The history was rewritten with `git filter-repo` for security only:

- the server address, account identifiers and local file-system paths are replaced by
  `<VPS_IP>`, `<ACCOUNT_ID>`, `<HOME>` and `<SCRATCH>` in every commit;
- `Algorithm_Brieuc/` (a third party's code), `Claude Vault/` (an editor's configuration),
  scraped raw feeds (`_automation/*/_raw/`), log files and compiled binaries are removed from
  the history;
- secrets were never committed (`.env` files and `logs/` are ignored by git; a full-history
  scan with gitleaks finds none). The keys that were once exposed in the server's crontab, in
  May 2026, were revoked at the time.

Nothing else was edited: commit messages, dates, the French and English mixed through the
notes, the mistakes and their corrections are the originals. Because the history was rewritten,
commit hashes differ from the private repository's; `proof-of-edge/PROVENANCE.md` gives both.

## Orientation

- `README_ORIGINAL.md`, the original repository's README: the status in August 2026, the five rules, the
  lesson registry pointer. The repository's own guide to itself is `CLAUDE.md`, the instruction
  file kept for the coding assistant used throughout; it is the most faithful description of
  how the programme was run, constraints included.
- `_meta/lessons_registry.md` — the lesson registry (L11–L67 and candidates).
- `<AssetClass>/research/{active,archived}/` — one folder per study, each with its
  pre-registration, code, results and verdict.
- `strategies/`, `ftmo_live/`, `Portfolio/` — the deployed code, the live system and the
  portfolio tools.
- `PropFirms/`, `data/ftmo_portfolio/` — the prop-firm programme: rules verified against primary
  sources, the challenge specification, the funded-account studies.
- `_audit/` — the audits, including the security review of 2026-05-30.

Market data is not included (`data/raw/` and the caches are ignored); result tables and figures
are.

Code drafted with a coding assistant (Claude Code) and reviewed by the author; every question,
protocol, kill rule and verdict is the author's.
