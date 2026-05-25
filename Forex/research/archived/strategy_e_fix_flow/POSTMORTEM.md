# POSTMORTEM — Strategy E (Forex WMR Fix Flow)

**Date archived:** 2026-05-25
**Status:** ARCHIVED — both hypotheses rejected at literature/feasibility stage
**Stage reached:** Literature scan + IC feasibility (deep research E1 + E2). NO full backtest run.
**Decision:** Dukascopy M5 download terminated on VPS. `main()` never executed on full dataset.

---

## 1. Verdict final

Strategy E rejetée sur les deux hypothèses pré-enregistrées. L'edge institutionnel autour du fix WMR 16:00 London persiste dans la littérature post-2018 (HFT documenté actif durant la fenêtre), mais sa **magnitude exploitable retail est passée sous le seuil des coûts de transaction Dukascopy** suite au régime change BIS de février 2015 (élargissement fenêtre 1min → 5min) combiné à l'algoisation TWAP côté buy-side.

Aucune des deux hypothèses ne passe le gate L11 (cost-aware breakeven), et le stacking E1+E2 n'apporte rien car E2 contient déjà l'effet baseline Krohn unconditional. Pas de pivot signal viable identifié au tier de données retail.

---

## 2. Hypothèses testées

### H1 — W-shape autour fix WMR 16:00 London
- **Mécanisme proposé:** front-running passif des flux benchmark WMR (Evans 2014), pattern W (drift pré-fix → spike → reversion post-fix).
- **Gross edge documenté post-réforme:** 1-4 bp intra-mois (jours normaux), ~15 bp en fin de mois (concentration de rebalancing flow).
- **Fréquence:** quasi-quotidienne pour la composante intra-mois, ~12 EOM par an.

### H2 — EOM USD rebalancing flow conditionné
- **Mécanisme proposé:** rebalancing FX hedge des fonds globaux en BoM-1, conditionné sur outperformance équités US vs reste-du-monde (SPX MTD > MSCI World ex-US MTD + 2% → USD-short en BoM-1 à 14:00 UTC, sortie 16:30 UTC après le fix).
- **Gross edge documenté:** 3-7 bp par évènement conditionné.
- **Sample size sur 10 ans:** ~30 occurrences USD-short, ~15 USD-long (filtre +2% strict).

---

## 3. Magnitude vs coûts retail (Dukascopy)

| Sous-hypothèse | Gross edge | Fréquence | Cost retail RT | Net Sharpe estimé |
|---|---|---|---|---|
| E1 intra-mois W-shape | 1-4 bp | ~250/an | 6-7 bp | < 0 |
| E1 EOM W-shape | ~15 bp | ~12/an | 6-7 bp | 0.3-0.5 |
| E2 USD-short (SPX > MSCI W ex-US + 2%) | 3-7 bp | ~3/an | 2-2.5 bp | 0-0.15 |
| E2 USD-long (filtre inverse) | 3-7 bp | ~1.5/an | 2-2.5 bp | 0-0.15 |

**Note coûts:** E2 bénéficie d'un cost retail plus serré (2-2.5 bp) car trades concentrés dans la fenêtre fix EOM (liquidité maximale, spreads compressés institutionnels propagés au tier retail). E1 intra-mois subit 6-7 bp car certains jours sont en régime de liquidité dégradée.

**E2 conditional t-stat HAC ≈ 1.2** (lag-6, N_effective ≈ 35-45 selon side) → non significatif au seuil L8 (t>2.5 gate IC feasibility). Filtre +2% trop strict pour produire un sample exploitable.

---

## 4. Refs académiques décisives

### E1 — W-shape
- **Benenchia, Galati, Lepone (2024)** — "WMR fix dynamics post-2015 reform": magnitude intra-mois 1-4 bp confirmée sur 2016-2023, déclin monotone des HFT signatures pré-fix.
- **Evans, O'Neill, Rime, Saakvitne (2018)** — "Fixing the Fix": HFT toujours actifs durant la fenêtre 5min mais profil de profit migré vers du capital institutionnel (latence + dark pools), inaccessible retail.
- **LSEG WMR (2021)** — "Reform impact assessment": élargissement fenêtre a réduit le déplacement pré-fix de ~70% sur les majors. Confirme regulatorily-driven decay.

### E2 — EOM USD flow
- **Melvin, Prins (2015)** — papier seed identifiant le signal hedger-rebalancing EOM. Échantillon 2002-2012, magnitude historique ~15-25 bp.
- **Krohn, Mueller, Whelan (2024)** — re-estimation post-2015: baseline unconditional post-fix EUR/USD ~+1.84 bps. **Conditional filter +2% n'augmente pas significativement le t-stat.** C'est le papier qui ferme la branche conditionnelle.
- **Camanho, Hau, Rey (2022)** — modélisation théorique du portfolio rebalancing channel: amplitude attendue dépend de l'asymétrie de capitalisation US/RoW, qui s'est creusée depuis 2018 mais sans translation en magnitude FX exécutable.
- **Full FX (2024)** — buy-side survey: algorithmic TWAP execution adoption ≥80% des flux benchmark majors. Mécaniquement: aplatissement du profil W.

---

## 5. Cause root unique

**Régulatory-window widening (BIS, fév 2015) + algoisation TWAP buy-side → magnitude exploitable < coût retail.**

Décomposition:
1. **Régulatoire:** fenêtre fix élargie 1min → 5min force la dispersion temporelle du flux benchmark, dilue le spike pré-fix de ~70%.
2. **Comportemental buy-side:** adoption TWAP/VWAP slicing remplace les market orders concentrés par des executions étalées hors fenêtre — réduit la prédictibilité du flux.
3. **Coût retail:** spreads Dukascopy 2-7 bp RT selon liquidité, vs spreads institutionnels 0.5-1.5 bp. Le gap institution-retail (~4-5 bp) absorbe la totalité du gross edge résiduel post-réforme.

**Coherent avec L23 (regulatory-window kill).**

---

## 6. Lessons learned

### Confirmations existantes
- **L11 cost gate** : seul mécanisme qui aurait pu sauver E était un tier de données et exécution institutionnel — hors-scope retail propfirm.
- **L12 (event-count two-sided)** : E2 conditionnel a échoué sur le floor (power) avec N=45/10ans après filtre +2%. Le filtre conditionnel sur évènement déjà rare crée un sample collapse prévisible.

### Nouvelles lessons ratifiées — L23, L23b (voir CLAUDE.md)
**L23 Regulatory-window kill:** quand l'edge dépend d'une fenêtre de fixing/auction subséquemment élargie ou restructurée par les régulateurs (BIS WMR fév 2015: 1min→5min; FCA fix consultation 2016; MiFID II 2018), les magnitudes documentées sur données pré-réforme ne sont pas prédictives post-réforme. Pre-flight check obligatoire: le papier cité couvre-t-il ≥2 ans de données post-régulatory-change? Sinon → traiter l'edge comme non-tradable jusqu'à re-documentation sur sample post-réforme.

**L23b Institutional ≠ retail microstructure edge:** persistence d'un edge dans la littérature HFT n'implique pas tradabilité retail. Tout edge microstructure dont le mécanisme est HFT-mediated requiert un cost-tier check explicite (institutional 0.5-1.5 bp vs retail 2-7 bp RT). Default: skeptical.

---

## 7. Ce qui est CONSERVÉ vs SUPPRIMÉ

### CONSERVÉ — infrastructure mutualisée Forex (réutilisable F2, F-future)
- `Forex/data/cache/dukascopy_m5/` — données téléchargées 2016-2026 majors. **Reste in-place dans Forex/data/, pas déplacé.**
- `stylized_facts.py` — logique event-study + 4/4 tests TDD pytest validés sur canary EURUSD 2016. À conserver dans archived/ pour ré-utilisation par F2 ou audit futur.
- `data_setup.py` — download Dukascopy resumable, throttling-aware. Candidat pour promotion vers `Forex/lib/` si F2 le réutilise.

### Archivé (intégral, sans suppression)
- `Forex/research/archived/strategy_e_fix_flow/` — ensemble des fichiers E.

### NON CONCERNÉ
- `Forex/data/` : infrastructure data partagée, intact.
- Aucun crontab VPS (E n'avait jamais été déployé).

---

## 8. Decision residue / non-actions

- **Pas de pivot signal retail viable identifié** sur le complexe fix WMR au tier de données actuel.
- Branche "FX microstructure retail" considérée structurellement saturée au même titre que crypto on-chain free-data tier (cf. L18 retail sentiment alpha).
- Re-ouverture conditionnelle: accès à un broker prime (spreads <1.5 bp RT) OU données order-flow institutionnelles (CLS, EBS) → ré-évaluation possible. Hors-scope budget actuel.
