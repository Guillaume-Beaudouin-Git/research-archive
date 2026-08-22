# Entrée de log — session_A_filters (CANDIDAT, à merger par le mainteneur)
*Candidat de section, périmètre session_A_filters uniquement. Numérotation/intégration tranchées au merge. Ne PAS écrire dans le log partagé (collision sessions parallèles). Rien figé.*

---

## [2026-06] Skew research — session_A_filters (combinaisons indicateurs + filtres directionnels)

**Objectif** : briques skew+/faible-DD pour L7, univers FTMO. Discipline anti-mining (DSR déflaté, mécanisme pré-spécifié, filtré-vs-nu, additionnalité). Détail : `data/skew_research/session_A_filters/exploration_2026-06.md`.

**Résultat : 0 brique L7 neuve.** Baseline TSMOM nu SR 0,82 t=4,70 (edge trend connu). Filtré-vs-nu : 1/4 bat sa base (#1 MA200), 3/4 rejetés. DSR N=9 PASS mais seulement pour la famille TSMOM → l'**additionnalité** tue les candidats proches.

- **#1 MA200 sur trend court** — bat sa base nue (SR 0,43→0,65, skew 0,37→0,47) mais brique NON : short-leg morte (+1,22/−0,06=beta), SR<TSMOM nu 0,82, corr-TSMOM 0,44.
- **#2 Donch-lowvol** — REJETTE (0,30→0,23 ; Donchian daily mort).
- **#3 persist5** — REJETTE (0,42→0,34) ; **persistance = ADX bis** (coupe entrées précoces gagnantes).
- **#4 strongclass (crypto+com)** — REJETTE par additionnalité (**corr-TSMOM 0,69 = tuning moteur**) + MaxDD −18%→−22% (perte diversif).
- **#5 DD-sizing (vol égale L19)** — bat le TSMOM nu : SR 0,82→0,90, skew +0,02→**+0,42** (tronque queue gauche). MAIS **corr-TSMOM 0,95 = raffinement moteur, PAS brique**. → verser au book J1/G1 (à valider robustesse).

**Candidats-leçons (nommés, à numéroter au merge) :**
- « L'additionnalité (corr au TSMOM) juge la brique, pas le DSR » (#4 0,69 / #5 0,95 = variantes TSMOM ; DSR valide l'edge trend, pas une brique neuve).
- « Overlay de RISQUE améliore le skew ; filtre de SIGNAL ne fabrique pas de brique » (#5 sizing-DD skew +0,02→+0,42 vol égale ; #1-#4 filtres signal dégradent/tunent).
- « Filtre de persistance = ADX bis » (#3 SR 0,42→0,34 ; coupe les entrées précoces gagnantes).
- « Restreindre l'univers ≠ nouvel edge » (#4 corr 0,69, MaxDD pire ; sous-échantillon du même signal).
- « Two-sided : short-leg du trend court/fast morte = tilt beta » (#1 +1,22/−0,06, #3 +1,04/−0,43).

**Action hors-L7** : sizing-DD (#5) = raffinement de skew pour le book trend J1/G1 (overlay de risque, pas sleeve), à valider en robustesse avant adoption (ici 1 config canonique, pas de sweep).

**Statut** : 0 jour live, tout backtest. DSR déflaté Bailey-LdP N=9. Réconcilié archive (session_regime_filters, breakout_deepdive, IDEA_TSMOM — pas de re-preuve). Coordination : écrit uniquement dans `session_A_filters/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue mainteneur.
