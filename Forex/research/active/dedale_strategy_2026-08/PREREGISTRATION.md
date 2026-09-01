# Pré-enregistrement — reproduction et test de « Dédale »

Rédigé et figé AVANT tout calcul de Sharpe, tout backtest exécuté, toute lecture de résultat.
Référence de spec : `SPEC_DEDALE.md` (même dossier), config A (défaut de code) comme test
primaire, config B (démo H4-cross) comme sensibilité secondaire.

## 1. Hypothèses testées (formulées à l'avance)
- **H1 (incohérence Sharpe)** : le Sharpe correct de la config live de l'auteur, annualisé en
  √(trades/an) et net du taux sans risque, est très inférieur à 1,56 — l'écart provient
  majoritairement d'une annualisation en √252 appliquée à une série indexée par trade (~100
  trades/an), soit un facteur de gonflement attendu ≈ √(252/100) = 1,587 (L47). Test : recalculer
  le Sharpe sous les deux conventions d'annualisation et comparer.
- **H2 (carry vs signal)** : sur 2018-2024, la majorité du P&L net vient de l'accumulation de
  swap plutôt que du mouvement de prix — conséquence mécanique attendue du filtre
  `IS_NEGSWAP_ALLOWED=false` (§1.4 SPEC) combiné à la hausse des taux USD 2022-2024. Test :
  décomposer chaque trade en P&L prix (gross) et P&L swap, sommer séparément.
- **H3 (ce qui reste)** : une fois le swap retiré, les deux jambes (long/short) séparées et le
  régime découpé (2022-2024 vs le reste), le signal résiduel (bande de pivot 1:1 en direction
  swap-positive) n'a pas d'edge two-sided significatif — cohérent avec L45 (momentum-crypto-CFD
  fermé sur le même mécanisme structurel : filtre de swap = "long-only déguisé", ici en carry).

## 2. Données et échantillon
- 7 paires FX majeures USD, M1 vrai-UTC, cache local `<SCRATCH>
  m1_cache/{EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,USDCHF,NZDUSD}_M1.parquet`, couverture
  2007-01→2026-06 (déclarée par le fichier lui-même, vérifiée avant usage).
- Resampling en H1 (open=first, high=max, low=min, close=last) pour le moteur de backtest ; en
  W1 (Mon 00:00 UTC → Sun 23:59 UTC, label=dimanche) pour les pivots — **approximation déclarée**
  de la semaine "broker" réelle (souvent ancrée en heure serveur EET/EEST, cf. L52) : nous
  n'avons pas cette information pour ce courtier précis, donc utilisation de la semaine
  calendaire UTC comme convention la plus neutre.
- Différentiel de taux directeur : `data/panels/fx_rates_3m.csv` (taux 3M interbancaires
  mensuels, USD/EUR/GBP/JPY/AUD/NZD/CAD/CHF, 2005-2026), ffill journalier intra-mois (max 1
  mois), comme proxy du swap réel — **approximation déclarée par le mandat lui-même**, pas les
  swaps facturés réels du courtier de l'auteur (indisponibles sur 2018-2024).
- Fenêtre de réplication primaire : **2018-01-05 → 2024-07-29** (fenêtre exacte revendiquée).
  Fenêtre étendue : tout l'historique disponible en cache (2007-01 → 2026-06), avec un warm-up
  d'au moins 1 semaine avant le premier trade pour disposer d'un pivot valide.

## 3. Modèle d'exécution (déclaré avant résultat)
- **Delay-1** : le signal est évalué à la clôture du bar H1 t ; l'entrée est exécutée à
  l'ouverture du bar H1 t+1 (jamais même-barre).
- **Détection SL/TP** : sur le high/low du bar H1 courant, dans l'ordre séquentiel de la
  simulation ; si un bar touche à la fois SL et TP (rare à H1, possible sur gap), **convention
  conservatrice : SL prioritaire** (cf. L59 — ne jamais supposer un remplissage favorable).
  Limitation déclarée : la détection à la granularité H1 (et non tick) peut manquer des touches
  SL/TP intra-heure très ponctuelles ; c'est un biais de PRUDENCE modérée dans les deux sens (peu
  de raison de penser qu'il favorise systématiquement le signal ou son absence), pas corrigé
  a posteriori.
- **Sizing** : risque fixe 1 % du solde courant (composé), converti en notionnel équivalent USD
  via `notional = risk_amount / (|entrée-SL| / entrée)` — la mécanique R-multiple, invariante à
  la devise de cotation (cf. justification §3 SPEC).
- **Coûts** — barèmes fixes déclarés par le mandat, appliqués au notionnel à l'aller-retour :
  0 bps (gross), 0,75 bps RT (Eightcap Raw), 2,48 bps RT (FTMO retail).
- **Swap** — proxy différentiel de taux, appliqué chaque nuit détenue (× 3 le mercredi soir,
  convention standard FX broker pour couvrir le week-end — pas vérifiée pour le courtier réel de
  l'auteur, déclarée comme approximation), avec DEUX variantes rapportées séparément :
  - `swap_brut` : différentiel de taux sans haircut (borne haute, optimiste) ;
  - `swap_realiste` : différentiel × 0,85 (haircut de markup, cohérent avec le repo —
    `sleeve_search_2026-08-06` mesure un différentiel réalisé à 89 % du taux sans risque sur un
    échantillon comparable ; nous prenons 0,85 comme approximation légèrement plus conservatrice,
    déclarée, pas calibrée sur ce jeu de données).
- **Filtre swap-directionnel** : la direction long/short n'est autorisée que si le différentiel
  de taux (net du haircut appliqué à la variante considérée) est strictement positif dans ce
  sens ; sinon aucun trade n'est ouvert sur cette paire à cette date (fidèle à
  `IS_NEGSWAP_ALLOWED=false`).

## 4. Méthodologie statistique (fixée avant résultat)
- **Sharpe** : rendements en excès du taux sans risque (DTB3/365 par jour de détention),
  annualisés en **√(trades/an)** — jamais √252 sur une série indexée par trade (L47) — ET,
  séparément, reporté sous la convention **erronée** √252 pour quantifier explicitement l'écart
  avec le 1,56 revendiqué.
- **HAC** : Newey-West lag 6 sur la série de rendements par trade (proxy de l'autocorrélation
  inter-trade due au chevauchement de tenue ~11j).
- **Two-sided (L25)** : jambe longue et jambe courte rapportées et testées séparément, jamais
  fusionnées avant analyse.
- **Walk-forward** : ≥5 folds expanding-window, découpage additionnel dédié 2022-2024 vs
  reste-de-l'échantillon (l'auteur affirme lui-même que c'est la période qui porte le
  résultat).
- **DSR** (pas PSR) si un quelconque degré de liberté de calibration est exercé de notre côté
  (aucun prévu au-delà de la config A/B déjà figées ci-dessus — donc n_essais_notre_part = 2,
  déclaré).
- **Bootstrap** : block-bootstrap (Politis-Romano), jamais iid, blocs dimensionnés sur la durée
  de détention moyenne.
- **Placebo apparié** : direction aléatoire (au lieu de swap-positive) avec la même mécanique de
  pivot/sizing, pour vérifier si le filtre de swap ajoute un signal au-delà d'un simple biais
  directionnel constant.
- **Benchmark** : S&P 500 (^GSPC via cache si disponible, sinon buy-and-hold déclaré à ~13 %/an
  cité par le mandat) sur la même fenêtre exacte.
- **Multiple testing** : n_tests cumulé avant cette hypothèse = 1 989 (ledger canonique,
  `_meta/n_tests_ledger.md`). Cette hypothèse ajoute **1** test enregistré (H2 carry-decomposition
  est un test DÉRIVÉ de H1, pas un essai indépendant supplémentaire — meilleure pratique :
  compter le hasard/l'hypothèse de recherche, pas chaque angle de reporting du même jeu de
  données). Seuil AMTP (Šidák) rapporté à n=1 990 dans le rapport final.

## 5. Ce qui ferait échouer/réussir chaque hypothèse (critère fixé à l'avance)
- H1 confirmée si le facteur d'écart mesuré entre Sharpe √(trades/an) et Sharpe √252 est dans
  [1.3, 2.0] (englobant 1,587 avec marge) ET explique ≥60 % de l'écart total avec 1,56.
- H2 confirmée si part_swap / (part_swap + part_prix) > 50 % sur le P&L net cumulé 2018-2024,
  variante swap_realiste.
- H3 confirmée si, net-de-swap réaliste, le t-stat HAC de la jambe combinée (long+short pondérée)
  ne dépasse pas le seuil AMTP à n=1990 sur au moins 3 des 5 folds walk-forward.

## 6. Contraintes d'exécution
Aucun moniteur, aucune boucle d'attente. Backtest lancé en arrière-plan par paire avec écriture
incrémentale (`trades_<PAIR>.csv`) pendant la rédaction du reste du rapport. `/usr/bin/python3`
uniquement. Écriture confinée à
`Forex/research/active/dedale_strategy_2026-08/`. Pas de push, pas de merge.
