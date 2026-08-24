# PropFirms — Propfirm Rules Documentation

## Purpose
Authoritative source for propfirm rules used in sizing analysis and challenge planning.
CLAUDE.md must reference this directory for all propfirm-specific numbers.

## Conventions
- `last_verified`: Date rules were confirmed against official help center
- `⚠️ UNVERIFIED`: Figure from training data / session context, not confirmed from official URL
- `✓ CONFIRMED`: Figure confirmed from official source (URL listed in sources.md)
- All dollar amounts are in USD
- DD = maximum drawdown allowed before bust
- DLL = Daily Loss Limit

## Scope
Active propfirm accounts or candidates for future challenges (état 2026-08-24 — voir
"Historique des décisions" ci-dessous, cette table a été périmée deux mois avant correction) :
| Firm | Status | Primary account |
|------|--------|-----------------|
| FTMO | LIVE (CFD book, Multi_Asset sleeves) | 10k, voir `PropFirms/ftmo/program_2026-06/` |
| Tradeify | **ANNULÉ 2026-06-10** — Strategy C sans véhicule (voir ci-dessous) | Select Flex $25K |
| Apex | CANDIDATE au cas par cas (dégel 2026-07-30, L51) — passer le test L53 avant toute sim | $25K–$100K |
| Topstep | CANDIDATE au cas par cas (dégel 2026-07-30, L51) — passer le test L53 avant toute sim | $50K–$150K |
| MFFU | CANDIDATE au cas par cas (dégel 2026-07-30, L51) — overnight autorisé sur tous les plans | $25K–$50K |
| Phidias | CANDIDATE (European) — non ré-audité par le dégel L51 | Various |

## Key rule: FTMO does NOT support CME futures
FTMO is explicitly excluded from futures strategies (CME MNQ/ES/ZN/CL). This is why Strategy C
(NQ opening momentum) has no FTMO vehicle and had a Tradeify candidacy — see below.

## Historique des décisions (Strategy C / véhicules futures)
- **2026-06-10 — Tradeify ANNULÉ.** Strategy C (NQ opening momentum) perd son véhicule Tradeify ;
  raison à l'origine de la recherche de pivot : FTMO ne finance pas les futures CME (L22c).
  Infra Strategy C conservée, réutilisable (`Futures/live/strategy_c_live/`), sans compte actif.
- **2026-06-10 — gel des firmes futures.** Décision de l'époque : « toutes les firmes futures
  daily-flat ⇒ tenues multi-jours disqualifiées » ⇒ Apex/Topstep/MFFU écartés en bloc.
- **2026-07-30 — dégel (L51, `CLAUDE.md` §Portfolio context).** Le gel de 2026-06-10 reposait sur
  un modèle mental ACTIONS (« daily-flat ⇒ pas de tenue multi-jours »), faux pour le CME : une
  règle daily-flat futures ne coupe que la pause de settlement, pas la session ; MyFundedFutures
  autorise l'overnight sur tous ses plans. Apex / Topstep / MFFU redeviennent **évaluables au cas
  par cas**, sous réserve du test **L53** en premier : si la marge du lot minimum tient dans le
  capital personnel, le propfirm n'apporte rien (mesuré sur ZN : compte perso dominant, voir
  `Multi_Asset/research/active/month_end_vehicle_2026-07/`).

## Files
- `comparison.md` — Side-by-side comparison table
- `<firm>/rules.md` — Full rules per firm
- `<firm>/sources.md` — URL sources + verification dates
