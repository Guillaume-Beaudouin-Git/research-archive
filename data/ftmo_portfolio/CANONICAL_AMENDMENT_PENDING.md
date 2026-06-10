# AMENDEMENT — APPLIQUÉ dans FTMO_CANONICAL_STATE.md (2026-06-10 soir, session v2.2 — dossier remonté)
*(APPLIQUÉ : inséré avant l'amendement v2.2 de FTMO_CANONICAL_STATE.md, session v2.2 du 2026-06-10 soir — ftmo_universe/ et ftmo_research/ remontés. Texte original : le dossier n'était plus monté — appliquer ce bloc en tête de la
section RÉCONCILIATION dès réaccès. Exigé par le contre-audit équipe v2.1, point 6.)*

## NOTE DE RÉOUVERTURE FORMELLE (2026-06-10)

Le verdict « CONFIRMÉ-CLOS, ne pas rouvrir sans preuve dure (§6) » a été levé dans ce cycle sous :
(a) **mandat MD explicite** (portefeuille multi-sleeves, horloges 6→3 mois, ML autorisé) ;
(b) **condition de réouverture #2 partiellement satisfaite PAR MESURE** : spread US100 à l'auction
mesuré 0.5 bps (518 jours M1), puis swaps/marges validés au terminal MT5 démo (modèle ±10%) —
le démo-60-trades reste un gate de déploiement, re-spécifié v2.1 : slippage ACTIF sur fills
16:00-16:30 Paris, ≥60 trades, logs commitées ;
(c) **changement d'objet** : v2.1 établit que le headline challenge ne repose PAS sur l'ORB
(compteur de jours ; P&L = −2.6 pts ; deadlock min-trading-days patché par token-trade) mais sur
l'overnight (+12.1 pts d'ablation iso-reste) + le séquencement variance/retries.

Les conditions #3 (OOS post-2026) et #4 (DSR>1 au niveau challenge) restent NON satisfaites au
sens strict — statut canonique : **« OUVERT SOUS CONDITIONS, v2.1 »**, pas « prouvé ».
Chiffres contractuels v2.1 (mono-stack, regen_all.py) : challenge pooled **84.8%** (IS 86.7 /
OOS 83.0), valeur funded **$1,204**, **EV +$699/campagne** ; plancher pessimiste si ORB mort au
coût réel : ~87% (token) / extraction $1,262 / **EV +$295**. Caveat ouvert : DSR 0.29 de la
sélection midweek overnight (grille 40 cellules) — sensibilité all-nights à trancher avant
signature. Conforme : réconciliation > régénération.
