# Current Focus — Algo_claude
**Last updated**: 2026-05-25  
*(Mettre à jour à chaque session. Ce fichier est opérationnel — CLAUDE.md est constitutionnel.)*

---

## Bloquants immédiats

### Strategy C — Démarrage paper trade
- Tradovate client construit, Test 2 signal engine = 10/10 match
- **BLOCKER 1**: VWAP granularity — vérifier que `tradovate_client.py` utilise des barres 1-min
  (pas 5-min resamplées) avant le premier trade. Backtest = 1-min exact.
- **BLOCKER 2**: Tests 1+3 (connexion Tradovate live/demo) non exécutés
- Action: `validate_tradovate.py` sur account demo, puis démarrer paper

---

## En cours

### Strategy B → Mainnet
- HL testnet actif depuis 2026-05-17, ~$16 accumulés (taux artificiels)
- 60 jours live requis → mainnet disponible ~2026-07-17
- Rien à faire — surveiller, puis switcher clé HL vers mainnet

### Commodities XS — Basis + TSMOM
- Sprint 3, Phase A non démarrée (checklist entière)
- 24 contrats yfinance (CL=F, GC=F, …) à télécharger + validation roll
- Action: `run_phase_a.py`, puis IC scan Phase B (S_TSMOM + S_BASIS)

### Automation pipeline
- Alpha hunt scraper fonctionnel, items en staging dans `promising/`
- Feasibility orchestrator opérationnel (SkipMonth + Generic handlers)
- **Stubs à compléter**: `ExitRuleHandler` et `RegimeFilterHandler` marqués
  `REQUIRES_HUMAN` dans le code — logique à implémenter
- Action: implémenter les deux handlers, tester sur hypothèses réelles

---

## Axes de recherche restants (par priorité)

| # | Axe | Type | Data | Effort |
|---|-----|------|------|--------|
| 1 | FTMO challenge analysis (Strat A) | Simulation | Interne | ~2h |
| 2 | Commodities XS IC scan (Sprint 3) | IC feasibility | yfinance | ~4h |
| 3 | Token unlock cliff shorts | Event-driven IC | TokenUnlocks.app | ~4h |
| 4 | HLP vault flow contrarian | HL-native IC | HL API | ~3h |
| 5 | GitHub commit velocity CS | Alt-data IC | GitHub REST | ~3h |
| 6 | Glassnode stablecoin flows | On-chain IC | ~$500/mo | Budget requis |

### Decisions pendantes
- **Propfirm Strategy A**: Propr compte breached. FTMO (5% daily DD, ~60% pass rate
  estimé) vs nouveau compte Propr (39% structural ceiling). Lancer la simulation FTMO
  AVANT d'acheter un nouveau compte.
- **Strategy C paper go/no-go**: P(bust)=46.2% at 3 MNQ/$1,000 trailing DD.
  Vérifier si sizing 2 MNQ donne P(bust) < 30% avant de commencer.
