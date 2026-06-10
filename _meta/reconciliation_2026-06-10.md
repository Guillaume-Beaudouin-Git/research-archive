# Réconciliation constitutionnelle L-series + intégrité du registre — 2026-06-10

*Maintenance, zéro trial, zéro contact data. Commits : CLAUDE.md (gravure seule) + outillage/rapport.*

## 1. Diagnostic — CLAUDE.md était PÉRIMÉ, pas tronqué ; le grep de session_I était CORRECT

- Max gravé avant cette session : **L24** (gravé set : L11-L15, L17-L24 + L11b/L12b/L23b ; trou **L16**).
- `git log -p --follow CLAUDE.md` : **aucune ligne L25+ n'a jamais été retirée** — L25-L44 n'ont
  JAMAIS été gravés (pas un effet de la consolidation P2). `CLAUDE.md.vps` : aucun L.
- Cause racine : les arcs 2026-06 ont minté des leçons en session avec la mention « numérotation
  tranchée au merge » — et le merge n'a jamais eu lieu. Cas limite documenté : chacune des deux
  parties croyait que L36 était « déjà dans CLAUDE.md » (`FTMO_LOG_overnight_candidate.md` NB vs
  l'annexe `_FTMO_ETAT_CANONIQUE.md`) — le « L36 √52 » était un fantôme.
- Sweep : **471 citations / 119 fichiers** pour L25-L44 (`grep -rnE "\bL(2[5-9]|3[0-9]|4[0-4])"`).

## 2. Table de réconciliation (source de vérité : rapport mintant > rapports ultérieurs > profils)

| L | Minté dans (origine) | Décision |
|---|---|---|
| L25 two-sided | `ftmo_research/FTMO_decision_memo.md` (06-02) | **gravé L25** |
| L26 delay-1/same-bar | idem | **gravé L26** |
| L27 spread-drift ≠ two-sided | idem (statarb) | **gravé L27** |
| L28 financing 2-jambes | idem | **gravé L28** |
| L29 half-life nécessaire≠suffisant | idem | **gravé L29** |
| L30 swap-sign (Dédale) | idem + `ftmo_swaps.py` | **gravé L30** |
| L31 alpha-decay OOS | idem ; confirmé backwardation/announcement/session_G | **gravé L31** |
| L32 carry uncollectable | thread commod_carry ; `CARRY_FEASIBILITY.md` | **gravé L32** |
| L32b collectable=credit | `backwardation_oil/report.md` (T109, 06-10) | **gravé L32b** |
| L33 cost-structure-decides | `_FTMO_ETAT_CANONIQUE.md` §7 (06-03) + session_F (held notional) | **gravé L33** (premier minté) |
| « L33 candidate » crypto-CFD TSMOM | `Crypto/research/active/ftmo_twoSided_makeOrBreak/POSTMORTEM.md` §5 | **renuméroté L45** (collision) |
| « L33-bis » spread executioner | session_G (06-04) | **gravé L33b** (convention maison) |
| L34 institutional-tier FX | `fix_reversal` (06-02, re-validé 06-10) ; cité fx_intraday B6/SYNTHESIS, current_focus | **gravé L34** (usage downstream unanime) |
| « L34 (proposé) » honesty checklist | `_FTMO_ETAT_CANONIQUE.md` §7 + `ORB_reconciliation` | **renuméroté L46** (collision) |
| L35 DP-ceiling | `ORB_reconciliation_2026-06.md` | **gravé L35** |
| L36 aggregate-overnight-carry | texte session_F (06-04), numéro assigné par l'usage session_G/E2/H | **gravé L36** |
| « L36 √52 » (fantôme) | annexe ETAT (06-03), jamais gravé, jamais cité par un rapport de kill | **renuméroté L47** |
| L37 filter-sanity / L38 beta-orthogonal / L39 skew daily-vs-monthly | `STRATEGY_RESEARCH_LOG.md` (trend arc 06-06) | **gravés L37-L39** |
| L40/L41 | arc top10-rigorous — **rapport ABSENT du repo** (mémoire de session seule) | **réservés**, ne pas réattribuer |
| L42 pré-FOMC drift réel | origine top10 (hors-repo) ; cité `paper_triage/PAPER_TRIAGE.md` + fx_intraday PRE_REG §H2 | **gravé L42** avec caveat d'origine |
| L43 FX intraday-flat cost-dead / L44 contraste XS mécanisme | `fx_intraday_deepdive/SYNTHESIS.md` (06-10) | **gravés L43-L44** |
| session_H registry-sweep | `data/skew_research/session_H_calendar_flow/report.md` | **gravé L48** (mint mandaté) |
| session_I unlock-beta / funding-momentum | `Crypto/research/active/session_I_crypto_flows/report.md` | **gravés L49 / L50** (mints mandatés) |
| L16 | jamais gravé ; 2 candidats flottants non ratifiés ; g1 audit : « L16 n'existe pas » | **vacant**, ne pas réattribuer |

Collisions : résolution « premier-minté garde le numéro » ; les artefacts historiques ne sont PAS
réécrits — table d'**aliases historiques** ajoutée dans CLAUDE.md (L45/L46/L47/L33b + L16/L40-41).

## 3. Convention de sweep (codifiée — le « grep failure » n'en était pas un)

session_I avait raison (« max graven = L24 ») ; le doute venait de l'écart constitution/usage.
Codifié dans CLAUDE.md §Parallel session coordination : sweep = anciens chemins cités
(`data/ftmo_research/`, `research/`, `data/oxfordstrat_109/`) + dirs consolidés + `data/
skew_research/session_*` + funnel CSVs ; **plus aucun minting de numéro en session** (candidats
NOMMÉS uniquement, numérotation à la réconciliation).

## 4. Intégrité du registre (Phase 3)

`tools/check_register_integrity.py` (fail-loud, exit≠0) : (a) toute citation backtick de
REGISTER.md doit résoudre sur disque (aliases de consolidation appliqués, citations non réécrites)
ET être git-trackée ; (b) chaîne N du ledger strictement monotone + incréments réconciliés.
**Premier run : 18 findings** → corrigés : 3 = règle parser (noms de fichiers nus = sténo
contextuelle, non vérifiables) ; **14 artefacts cités mais non trackés** (REPORT paper_triage,
funnel all_trials/step2, AUDIT_REPORT, REPORT_S076, mtm_deployable.csv…, max 268K) → `git add`
ciblé. **Second run : clean** (chaîne [108, 112, 115, 117], deltas [4,3,0,2] ✓). Ajouté comme
étape de clôture OBLIGATOIRE dans CLAUDE.md.

## 5. État final

Registre constitutionnel : **L11 → L50** (gaps volontaires : L16 vacant, L40/L41 réservés).
Les trois candidats pendants (session_H, session_I ×2) sont gravés (L48-L50). Aucun rapport
historique modifié. REGISTER.md : intègre et machine-vérifiable à chaque clôture de session.
