# RAPPORT — Carry conditionnel FX (filtre de swap, post-Dédale)

Session dédiée, axe **carry conditionnel** : le swap comme **filtre d'entrée**, jamais comme
rendement. Prérequis lus intégralement avant tout code : `dedale_strategy_2026-08/RAPPORT.md`,
`dedale_config_2026-08/RAPPORT.md`, `dedale_broker_2026-08/RAPPORT_BROKER.md`,
`dedale_audit_2026-08/RAPPORT_AUDIT.md`, mémoire `fx_carry_dedale_2026-08`. Code : `code/`.
Résultats bruts : `results/*.csv`. Données : `data/daily_close.parquet` (9 paires, 2007-01 →
2026-08, closes UTC 00:00, extraites en lecture seule de `data/deep_history_utc/` (8 paires) et du
cache scratchpad M1 (GBPJPY, plus récent, jusqu'au 2026-08-28) — chemins absolus, jamais copiées).

## Réponse en quatre lignes

1. **Le filtre ne bat pas son placebo — verdict NÉGATIF et significatif sur l'historique complet.**
   Portefeuille équipondéré 9 paires, coût+swap FTMO réels : Sharpe **−0,594** (HAC t **−2,63**,
   bootstrap block CI95 **[−1,02 ; −0,17] — exclut zéro, entièrement négatif**), pire que le
   buy-and-hold (**−0,50**) et battu seulement par sa propre falsification inversée (**−0,71**).
   Sur les 9 paires prises séparément, seules **3/9** battent nettement leur placebo aléatoire
   (AUDJPY 94,5ᵉ percentile, USDCHF 88,0ᵉ, GBPJPY 93,5ᵉ) et **2/9 sont dans le pire décile**
   (USDCAD et GBPUSD, 13,5ᵉ chacune) — **pas un edge, un mélange de régimes de change opposés.**
2. **Point mort : 6 à 83 nuits selon la paire, contre 3 paires structurellement sans côté payant
   du tout (infini).** À coût FTMO (2,48 bps RT), seules AUDJPY (6,3 nuits) et GBPJPY (8,5) sont
   rentables dans l'horizon de portage typique (~10-14 j, calé sur Dédale). USDCHF est à la
   limite (11,3). USDJPY (15,9), USDCAD (49,6) et EURUSD (82,7) exigent des tenues bien
   au-delà de tout swing FX réaliste. AUDUSD/GBPUSD/NZDUSD n'ont **aucun côté positif** dans la
   table FTMO réelle — point mort infini, mortes par construction.
3. **Ce qui survit sous les taux 2026 : rien de neuf, et une paire s'inverse.** Le différentiel
   théorique 2026 (taux officiels Aug-2026 donnés) capture seulement **13 à 43 %** côté FTMO
   (AUDJPY 43 %, GBPJPY 39 %, USDCHF/USDJPY ~22 %, USDCAD 13 %) — confirme la fourchette du
   mandat, calculée indépendamment ici. La compression 2022-24→2026 (recalcul FRED indépendant,
   pas l'ESTIMATION du rapport broker) : USDJPY −40 %, GBPJPY −34 %, AUDJPY −16 %, **USDCHF
   ÉLARGI +14 %** (nouveau — hors du périmètre croix-JPY du rapport broker). Aucune paire ne
   passe d'un point mort intenable à un point mort viable sous ce régime.
4. **Véhicule : ni FTMO ni IBKR ne sauvent l'idée à l'échelle de trade réelle.** IBKR (~0,4-0,5
   bps annoncé) devient **plus cher que FTMO** au notionnel médian mesuré du système Dédale
   ($8 482, IBKR RT **4,72 bps** vs FTMO 2,48) à cause du minimum $2/ordre (L57) — et **44,5 bps**
   au notionnel minimum mesuré ($899). Le seuil de croisement où IBKR redevient moins cher que
   FTMO est ≈ $50-100k de notionnel par jambe — hors de portée d'un compte 12-15k€ à risque 1 %.

**Δn_tests = 1** (hypothèse unique : filtre de direction carry FRED historique, two-sided réel,
coûts+swaps FTMO mesurés, 9 paires, agrégé + jambes séparées = angles de reporting du même test,
convention du dépôt). Les études `dedale_strategy_2026-08`/`dedale_config_2026-08` avaient déjà
consommé leurs propres essais (n local 1990 sur leur ledger, hypothèse différente : filtre de
signe du swap COURANT dans l'EA, pas un différentiel historique trade-par-trade) — non retesté
ici, base et signal différents.

---

## 0. Ce qui n'a PAS été refait (acquis, cité, pas remesuré)

- Biais d'anticipation MT5 de l'EA original (`SYMBOL_SWAP_LONG` constant sur toute la passe) —
  démontré `dedale_audit_2026-08`. Sa version non biaisée : +16-21 %/6,5 ans.
- Long-only par bug (test de distance ligne 801 aveugle à la direction, 0/30 ventes acceptées).
- Sharpe 1,56 caduc → 0,68 gross / 0,48 excès (`dedale_strategy_2026-08`).
- Le squelette carry+pivot nu (config A, filtre = signe du swap COURANT, pas historique) est déjà
  classé **kill mécanique probable** par `dedale_strategy_2026-08` (n=1990, DSR 0,024, AMTP
  |t|>4,21 jamais atteint, max observé 2,26). **Cette session teste une hypothèse voisine mais
  distincte** : la direction pilotée par le **différentiel de taux historique** (FRED, trade par
  trade, jamais figé), et non par la lecture instantanée du swap du jour — décorrélée du moteur
  pivot/TDI de Dédale (pas de SL/TP intrabar ici, un position-holding pur, cf. §1).
- Compression du carry 2022-24→2026 sur les croix JPY (méthode "ESTIMATION" à la main,
  niveaux annuels) — `dedale_broker_2026-08/RAPPORT_BROKER.md` §2. Recalculée indépendamment ici
  §4 à partir des observations mensuelles FRED réelles (résultat proche mais pas identique — voir
  divergence AUDJPY notée).
- Table de swaps FTMO réelle 2026-09-02 (mandat) — **non calibrable contre du réel** : le seul
  fichier de swaps facturés sur le VPS (`data/ftmo_portfolio/swaps_billed_live.csv`, lecture
  seule, vérifié cette session) ne couvre que US100.cash/GER40.cash — le book funded n'a **jamais**
  tenu de jambe FX. La table est prise telle quelle ; sa cohérence structurelle (signe, ordre de
  grandeur, capture 13-43 % du différentiel théorique) est vérifiée indépendamment via FRED
  (§4.2), pas via un ticket de swap réel.

## 1. Méthode — moteur autonome, décorrélé du pivot Dédale

**Signal.** Pour la paire BASE/QUOTE, `diff_pp(t) = taux(BASE,t) − taux(QUOTE,t)` (FRED, taux
3M interbancaires mensuels, cache local lu directement, **aucun appel réseau** — cache re-lu tel
quel, `code/rates.py`). Discipline T-1 : la série mensuelle est décalée d'**un mois plein** avant
d'être plaquée sur le calendrier journalier (`ffill`) — une valeur connue pour le mois M n'est
utilisable qu'à partir du mois M+1. C'est plus conservateur que nécessaire (les taux 3M sont en
réalité connus en continu, pas seulement en fin de mois).

**Rebalancement.** Tous les **10 jours de bourse** (~2 semaines calendaires), calé sur la tenue
moyenne mesurée de Dédale (~11 j). Direction = signe du différentiel à la date de rebalancement,
position maintenue constante entre deux rebalancements. **Ce n'est délibérément PAS une
réplication du pivot/TDI de Dédale** — aucun stop, aucun take-profit intrabar : c'est un test
isolé du filtre de direction carry seul, sur un portage buy-and-hold entre rebalancements.

**Vol targeting journalier** (règle dure du dépôt) : vol réalisée 20j annualisée, levier =
10 %/vol_réalisée, plafonné à 3×.

**Coûts et swap.** Coût d'exécution RT appliqué aux jours de retournement de direction (turnover).
Swap = table réelle FTMO donnée (`code/swaps.py`), appliqué chaque nuit calendaire tenue,
convention **mercredi ×3** (T+2, standard FX). Rendements en excès du DTB3 (FRED), HAC lag-6
(`statsmodels`, `cov_type='HAC'`), bootstrap **block** (Politis-Romano, bloc=10j, 2000 réplications
vectorisées), walk-forward 5 folds expanding, MDE avec facteur de puissance 1,40 (L65).

**Témoins** (mêmes coûts, même mécanique, seule la direction change) :
- **Placebo aléatoire apparié** : même cadence de rebalancement, direction tirée ±1 (50/50),
  200 tirages par paire → distribution de Sharpe, percentile du résultat réel dedans.
- **Falsification (inverse)** : direction = −signe(différentiel réel).
- **Buy-and-hold** : toujours long, mêmes coûts/swap.

Code : `code/engine.py` (moteur), `code/rates.py` (différentiel FRED), `code/swaps.py` (table),
`code/stats_tools.py` (HAC, bootstrap, WF, MDE), `code/run_all.py` (orchestration Parts A/D),
`code/compression.py` (Parts B/C), `code/vehicle.py` (Part E).

## 2. Partie A — le filtre bat-il son placebo ?

### 2.1 Portefeuille agrégé (9 paires équipondérées, coût FTMO 2,48 bps RT)

| Fenêtre | n | Sharpe réel | HAC t | Bootstrap CI95 | Reverse | Buy-hold | MDE (L65) | \|effet\|/MDE |
|---|---|---|---|---|---|---|---|---|
| **2007-2026 (complet)** | 5119 | **−0,594** | **−2,63** | **[−1,02 ; −0,17]** | −0,706 | −0,499 | 0,618 | **0,96** |
| 2018-2024 (fenêtre Dédale) | 1711 | −0,374 | −0,95 | [−1,08 ; 0,41] | −1,531 | −0,633 | 1,070 | 0,35 (sous-puissant) |
| 2026 seul | 171 | +0,283 | 0,23 | [−1,93 ; 2,59] | −1,934 | 0,247 | 3,383 | 0,08 (très sous-puissant) |

**Sur l'historique complet — le seul point correctement doté en puissance (ratio effet/MDE ≈ 1) —
le résultat est négatif, HAC-significatif, et son CI95 exclut zéro.** Walk-forward sur la fenêtre
primaire : **1/5 folds positifs (20 %)**, sous le seuil RESEARCH_PASS (WF>50 %) et sous le 50 %
déjà mesuré par `dedale_strategy_2026-08` sur le squelette carry+pivot (config A). **La fenêtre
Dédale et la fenêtre 2026 sont TOUTES DEUX sous-puissantes** (ratio effet/MDE < 0,4) : aucune
conclusion fiable n'est possible sur elles isolément — seul le verdict sur les 19 ans complets
est solide.

Ordre : buy-hold (−0,50) > réel (−0,59) > inverse (−0,71) sur l'historique complet — **la
direction pilotée par le carry ajoute un peu de valeur par rapport à sa propre falsification, mais
reste pire que ne rien filtrer du tout.** Répond au point 4.2 de `dedale_strategy_2026-08` (le
placebo aléatoire y battait aussi la direction réelle sur l'historique étendu) — **même verdict,
moteur totalement indépendant, signal différent (FRED historique vs swap courant), résultat
identique.**

### 2.2 Par paire (historique complet, percentile vs 200 tirages placebo)

| Paire | Sharpe réel | HAC t | Percentile vs placebo | Verdict |
|---|---|---|---|---|
| **AUDJPY** | 0,036 | 0,16 | **94,5ᵉ** | bat le placebo nettement |
| **USDCHF** | −0,161 | −0,70 | **88,0ᵉ** | bat le placebo (les deux restent négatifs en absolu) |
| **GBPJPY** | −0,013 | −0,06 | **93,5ᵉ** | bat le placebo nettement |
| AUDUSD | −0,246 | −1,08 | 75,5ᵉ | au-dessus de la médiane |
| USDJPY | −0,326 | −1,46 | 58,5ᵉ | proche de la médiane |
| NZDUSD | −0,402 | −1,77 | 36,5ᵉ | sous la médiane |
| EURUSD | −0,451 | −2,01 | 35,0ᵉ | sous la médiane |
| **USDCAD** | −0,644 | **−2,82** | **13,5ᵉ** | pire que 86,5 % des tirages aléatoires |
| **GBPUSD** | −0,626 | **−2,77** | **13,5ᵉ** | pire que 86,5 % des tirages aléatoires |

**Lecture honnête** : 3 paires (toutes des croix ou quasi-croix JPY à fort différentiel) battent
nettement leur placebo ; 2 paires (USDCAD, GBPUSD — différentiel structurellement faible, cf. §4)
sont dans le pire décile. **Ce n'est pas un edge cohérent, c'est le signal du différentiel qui
fonctionne exactement là où le différentiel est large (JPY-financé) et se comporte comme du bruit,
voire pire, là où il est proche de zéro** — cohérent avec le mécanisme documenté en §4 : un signal
de signe sur un différentiel proche de zéro est numériquement instable (bascules fréquentes,
turnover élevé, coût qui domine). **Détail complet** : `results/part_a_filter_vs_placebo.csv`.

## 3. Partie D — two-sided obligatoire (L25) : le filtre carry est-il vraiment deux jambes ?

Pourcentage de jours où chaque jambe est active (`results/part_d_two_sided_legs.csv`) :

| Paire | Long (complet) | Short (complet) | Long (2018-24) | Short (2018-24) |
|---|---|---|---|---|
| **AUDJPY** | **99,6 %** | **0,0 %** | **100 %** | **0,0 %** |
| **GBPJPY** | **99,6 %** | **0,0 %** | **100 %** | **0,0 %** |
| USDJPY | 62,5 % | 37,1 % | **100 %** | **0,0 %** |
| USDCHF | 85,3 % | 14,3 % | **100 %** | **0,0 %** |
| EURUSD | 39,0 % | 60,6 % | **0,0 %** | **100 %** |
| USDCAD | 37,3 % | 62,2 % | 57,1 % | 42,9 % |
| AUDUSD | 65,4 % | 34,2 % | 18,5 % | 81,5 % |
| GBPUSD | 69,3 % | 30,3 % | 34,5 % | 65,5 % |
| NZDUSD | 83,3 % | 16,2 % | 71,9 % | 28,1 % |

**AUDJPY et GBPJPY ne sont JAMAIS passées short sur 19,4 ans complets** (JPY a été la devise la
plus basse-taux du G10 sur la quasi-totalité de la période) — le filtre "two-sided" y est
**long-only par construction structurelle, pas par bug**, mais le résultat pour L37 est identique :
*« si sign(filtre) ≠ signal natif <5 % du temps, le filtre est cosmétique »*. Sur ces deux paires,
le filtre carry EST le signal long-only du yen faible, pas un filtre bidirectionnel. **Sur la
fenêtre précise citée par Dédale (2018-2024), quatre paires sur neuf (AUDJPY, GBPJPY, USDJPY,
USDCHF) sont 100 % long et trois autres sont ≥57 % dans un seul sens (EURUSD 100 % short,
USDCAD 57 % long) — le "two-sided" de cette fenêtre est presque entièrement un pari de régime
unique (USD/AUD/GBP en hausse de taux vs JPY/EUR faibles), pas un signal symétrique.** Confirme
directement §4.2 de `dedale_strategy_2026-08` (2022-2024 = pire régime dans SA reproduction) sous
un angle indépendant : ce n'est pas que le filtre technique de Dédale a raté ce régime, c'est que
le régime **est** le signal sur la majorité des paires de son propre univers cité.
⚠ Note technique : les jambes à 0 % d'activité affichent un Sharpe/t artefactuel dans le CSV brut
(rendement en excès = −RF constant sur une position nulle, ratio numériquement instable) — ignorés
ici, seul le % d'activité est interprété.

## 4. Partie B/C — point mort en nuits, et ce qui survit à la compression 2026

### 4.1 Point mort face au coût d'exécution (table FTMO réelle, mesurée 2026-09-02)

| Paire | Côté payant | Swap reçu (bps/nuit) | Point mort FTMO (2,48 bps) | Point mort Eightcap (~0,90 bps est.) | Point mort IBKR-exécution (~0,45 bps) |
|---|---|---|---|---|---|
| AUDJPY | long | +0,393 | **6,3 nuits** | 2,3 | 1,1 |
| GBPJPY | long | +0,291 | **8,5 nuits** | 3,1 | 1,5 |
| USDCHF | long | +0,219 | **11,3 nuits** | 4,1 | 2,1 |
| USDJPY | long | +0,156 | **15,9 nuits** | 5,8 | 2,9 |
| USDCAD | long | +0,050 | **49,6 nuits** | 18,0 | 9,0 |
| EURUSD | short | +0,030 | **82,7 nuits** | 30,0 | 15,0 |
| AUDUSD | aucun | −0,489/−0,888 | **∞** | ∞ | ∞ |
| GBPUSD | aucun | −0,341/−0,436 | **∞** | ∞ | ∞ |
| NZDUSD | aucun | −0,613/−0,128 | **∞** | ∞ | ∞ |

Comparé à la tenue moyenne réaliste (~10-14 j, calée sur Dédale et sur le rebalancement de cette
étude) : **seules AUDJPY et GBPJPY sont rentables à coût FTMO dans un horizon de portage
ordinaire ; USDCHF est à la limite.** Les trois autres paires à côté payant nécessitent des tenues
de 7 semaines à 4 mois — hors du régime de tenue de toute stratégie swing FX documentée dans ce
dépôt. **Trois paires sur neuf n'ont structurellement AUCUN côté payant** : y tenir une position,
dans QUELQUE sens que ce soit, coûte du swap chaque nuit — point mort infini, mortes par
construction, cohérent avec `dedale_strategy_2026-08` qui les gardait "perdantes" sans les
exclure. Table complète : `results/part_bc_compression_breakeven.csv`.

### 4.2 Capture du différentiel théorique — vérification structurelle du mandat

Différentiel théorique **point-in-time Aug-2026** (taux directeurs officiels donnés dans le
mandat, recalculé indépendamment ici, `code/compression.py`) vs swap réellement reçu (table
FTMO) :

| Paire | Théorique 2026 (bps/nuit) | Reçu FTMO (bps/nuit) | Capture |
|---|---|---|---|
| AUDJPY | 0,918 | 0,393 | **42,8 %** |
| GBPJPY | 0,753 | 0,291 | **38,6 %** |
| USDCHF | 0,993 | 0,219 | **22,1 %** |
| USDJPY | 0,719 | 0,156 | **21,7 %** |
| USDCAD | 0,377 | 0,050 | **13,3 %** |

**Confirme exactement la fourchette du mandat (13-43 %) par un calcul indépendant** — le markup
FTMO (L28 : point fixe marqué des deux côtés) capture **57 à 87 %** du différentiel théorique
avant même de parler de coût d'exécution. Ce n'est pas un fait qui dépend du calibrage absolu de
la table (non calibrable ici, §0) : c'est un ratio entre deux mesures indépendantes (taux
officiels FRED/banques centrales vs table FTMO donnée), structurellement robuste.

### 4.3 Compression 2022-24 → 2026 (recalcul FRED indépendant, moyennes mensuelles réelles)

| Paire | Différentiel 2022-24 (bps/nuit) | Différentiel 2026 YTD (bps/nuit)† | Δ |
|---|---|---|---|
| USDJPY | 1,096 | 0,654 | **−40,3 %** |
| GBPJPY | 1,077 | 0,711 | **−34,0 %** |
| AUDJPY | 0,899 | 0,759 | **−15,6 %** |
| **USDCHF** | 0,875 | 0,995 | **+13,8 % (ÉLARGI)** |
| USDCAD | 0,080 | 0,377 | élargi en absolu, mais parti d'une base quasi nulle (%  non interprétable) |
| EURUSD/AUDUSD/GBPUSD/NZDUSD | proches de zéro dans les deux fenêtres | proches de zéro | bruit, cohérent avec §4.1 "aucun côté payant" |

† ⚠ **fenêtre "2026 YTD" ici = janvier-mars 2026 en pratique** : la série FRED JPY 3M
interbancaire s'arrête en mars 2026 dans le cache local (pas d'appel réseau ce jour, cache lu tel
quel) — toute observation où JPY est manquant est droppée de la moyenne. C'est **plus ancien** que
le point-in-time Aug-2026 utilisé en §4.2 (taux directeurs officiels donnés dans le mandat, pas
FRED) — d'où un léger désaccord de niveau avec `dedale_broker_2026-08/RAPPORT_BROKER.md` sur
AUD/JPY (celui-ci annonçait un ÉLARGISSEMENT +4 % en méthode "ESTIMATION niveaux annuels" à Aug
2026 ; ce recalcul FRED, tronqué à mars 2026, indique encore une COMPRESSION −15,6 %). Direction
qualitative identique sur USDJPY/GBPJPY (compression forte, confirmée par les deux méthodes et les
deux fenêtres) ; **AUDJPY est le point de désaccord, à trancher par le point-in-time Aug-2026 du
§4.2 (0,918 bps, cohérent avec le rapport broker) plutôt que par cette moyenne tronquée.**
**USDCHF/USDCAD sont un ajout net de cette session** (hors périmètre croix-JPY du rapport broker)
: le franc suisse n'a PAS suivi le mouvement de compression généralisé — la Fed reste ~3,6 points
au-dessus de la BNS à taux zéro, un différentiel plus large qu'en 2022-24, pas plus étroit.

**Verdict Partie C : rien ne devient viable sous les taux 2026 qui ne l'était pas déjà — les deux
seules paires avec un point mort tenable (AUDJPY, GBPJPY) le restent, mais leur différentiel
théorique a lui aussi reculé (−16 %, −34 %) ; USDCHF, seule paire dont le différentiel s'élargit,
reste à la limite du point mort (11,3 nuits) et n'est pas assez rentable pour changer le verdict.**

## 5. Partie E — véhicule : le coût fixe renverse le classement à l'échelle réelle

`dedale_broker_2026-08/RAPPORT_BROKER.md` concluait *« IBKR > Eightcap »* sur un raisonnement en
bps/RT publiés (IBKR ~0,4-0,5 bps vs Eightcap ~0,66-1,18 bps ESTIMATION) — **correct en ordre de
grandeur mais qui ignore L57 (le coût fixe domine sur petit notionnel)**. IBKR facture un minimum
de **2 $/ordre** ; au notionnel réellement mesuré par cette même étude sur les vrais trades
Dédale (`trades_CONFIRMED_extended_primary.csv`, colonne `notional_per_risk_unit`, cité dans
`dedale_broker_2026-08` §4.3) :

| Notionnel par trade | Cas | IBKR RT effectif | vs FTMO 2,48 bps |
|---|---|---|---|
| **$8 482** (médiane des 290 trades réels) | trade typique | **4,72 bps** | **PLUS CHER** |
| **$899** (minimum mesuré, AUDUSD sell 2020-03-18) | choc de vol | **44,5 bps** | **18× plus cher** |
| $50 000 | seuil de croisement | 0,80 bps | moins cher |
| $100 000+ | 1 lot standard | 0,40 bps | conforme au chiffre annoncé |

**Le chiffre "IBKR moins cher" du rapport broker n'est vrai qu'au-delà de ~$50-100k de notionnel
par jambe — hors de portée d'un compte 12-15k€ à risque 1 %/trade (jamais plus de quelques
milliers de dollars de notionnel, cf. la granularité mesurée dans le rapport broker lui-même,
0,01-0,08 lot).** À l'échelle réelle de cette stratégie, **FTMO (CFD, coût plat en bps) est
structurellement MOINS cher qu'IBKR (coût plancher en dollars)** — l'inverse du verdict du rapport
précédent, qui raisonnait en bps publiés sans reporter au notionnel effectivement tradé. Ceci ne
change PAS le mécanisme de portage (L28 toujours vrai : le swap CFD FTMO reste un point fixe
marqué des deux côtés, contre l'intérêt de marché ± spread publié d'IBKR) — mais sur le COÛT
D'EXÉCUTION, à cette échelle de compte, FTMO l'emporte. Eightcap reste non testable : sa table de
swap n'a pas pu être obtenue (`dedale_broker_2026-08` §1, SPA JS, aucune donnée datée
extractible) — impossible de rejouer le même test de point mort pour ce courtier sans fabriquer un
chiffre. Code : `code/vehicle.py`.

**Verdict Partie E : aucun véhicule ne sauve l'idée.** FTMO gagne sur le coût d'exécution à cette
échelle mais reste plombé par son markup de swap (§4.2, 57-87 % du différentiel théorique capté
par le broker). IBKR gagnerait sur le mécanisme de portage (financement de marché, pas de point
fixe bidirectionnel) mais perd sur le coût d'exécution à cette échelle de compte — et son
financement FX n'a pas été chiffré en bps/nuit ici (mécanisme différent, hors du temps disponible
cette session — signalé, pas inventé).

## 6. Ce qui est solide vs ce qui est fragile

**Solide** (correctement doté en puissance, robuste à plusieurs méthodes) :
- Verdict négatif du portefeuille agrégé sur 19 ans (ratio effet/MDE ≈ 0,96, HAC t −2,63, CI95
  hors zéro).
- Capture du différentiel théorique par le markup FTMO, 13-43 %, confirmée par calcul indépendant.
- Trois paires (AUDUSD, GBPUSD, NZDUSD) structurellement sans côté payant — point mort infini,
  invariant à la méthode.
- Le caractère long-only structurel d'AUDJPY/GBPJPY sur l'historique complet (99,6-100 % actif
  d'un seul côté) — pas un artefact d'échantillon, 19,4 ans de données.

**Fragile / non concluant** :
- Les fenêtres 2018-2024 et 2026-seul sont toutes deux sous-puissantes (ratio effet/MDE < 0,4) —
  **aucune conclusion fiable sur le régime actuel isolément**, il faudra soit plus d'historique
  2026, soit accepter de ne trancher que sur le long terme.
- Le désaccord AUDJPY entre le recalcul FRED tronqué (§4.3, compression −16 %) et le point-in-time
  officiel (§4.2, cohérent avec le rapport broker, différentiel encore large 0,918 bps) — la
  version point-in-time est plus fiable (données à jour), mais le manque de série FRED JPY
  post-mars-2026 empêche une moyenne 2026 propre.
- La table de swap FTMO n'a pu être calibrée contre aucun ticket réel (le book funded n'a jamais
  tenu de jambe FX) — prise au mandat, cohérence uniquement structurelle (§0, §4.2).

## 7. Multiple testing

Δn_tests de cette session = **1** (hypothèse : direction pilotée par le différentiel de taux
historique FRED trade-par-trade, two-sided réel, coûts+swap FTMO réels, 9 paires — Parties A/B/C/D/E
sont des angles de reporting du même test enregistré, pas des essais indépendants, convention du
dépôt cf. `dedale_strategy_2026-08` §8). Ce test **ne revendique aucun PASS** — c'est un résultat
négatif (Sharpe agrégé négatif, HAC-significatif, CI95 hors zéro dans le sens défavorable) : la
correction AMTP, qui ne mord que sur des revendications positives, est sans objet ici. Le résultat
est cohérent avec, et renforce indépendamment, le kill mécanique déjà posé par
`dedale_strategy_2026-08` (n local 1990, DSR 0,024) sur une hypothèse voisine mais distincte
(signe du swap courant, pas différentiel historique).

## 8. Conclusion

**L'idée ne survit pas au markup — sur l'agrégat des 9 paires et sur l'historique complet, avec
un moteur indépendant du pivot Dédale, un signal de direction FRED historique jamais figé, et la
table de swap FTMO réellement mesurée.** Le carry conditionnel FX, filtré par le sens du portage,
rejoint le carry G10 (mort post-GFC) et le carry commodités CFD (L32b) dans la même famille de
mécanismes : un swap positif existe, mais (i) le broker en capte 57-87 % en markup avant même le
coût d'exécution, (ii) le point mort qui reste est intenable sur la majorité de l'univers testé,
et (iii) les deux paires qui font exception (AUDJPY, GBPJPY) le font parce qu'elles sont
long-only sur près de deux décennies — un pari sur le yen faible déguisé en filtre bidirectionnel,
pas un edge de portage. **Fermeture propre, famille CLOSE** (kill mécanique, catégorie non
rouvrable selon la politique du dépôt — le kill n'est ni un problème de véhicule, ni de coût
isolé, ni de puissance sur le point central, ni de géométrie).
