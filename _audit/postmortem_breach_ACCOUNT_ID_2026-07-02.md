# Post-mortem — breach compte FTMO <ACCOUNT_ID> (2026-07-02)

**Portée : LECTURE SEULE.** Analyse sur artefacts archivés du compte mort (<ACCOUNT_ID>,
FTMO-Server3). Le nouveau compte (<ACCOUNT_ID>, FTMO-Server2, armé 07:36 UTC) n'a PAS été touché.
Reconstruction via données terminal ; aucune logique de signal réimplémentée.

## Sources (toutes archivées, pull read-only du VPS)
- `MQL5/breach_snapshot_state_20260702_0711.json` (état EA à 07:10 UTC, post-breach)
- `MQL5/Files/{fills.csv, swaps_billed.csv, m5_today.json}` (non écrasés — nouveau compte flat)
- `MQL5/logs/20260702.log` + `logs/20260702.log` (journal terminal, **horodatage GMT+0 = UTC**)
- `Bases/FTMO-Server3/history/USDJPY/cache/M5.hc` (bougies M5 USDJPY, SoA parsée hors-ligne)
- `Bases/FTMO-Server3/ticks/USDJPY/ticks.dat` (cache ticks — n'a gardé que 07:21→07:36 UTC)
- logs cron `ftmo_brain/reconcile/watchdog`

**Fuseaux (verrouillés par recoupement mtime UTC ↔ ticks.dat ↔ journal) :**
serveur FTMO = UTC+3 (EEST) · Paris = UTC+2 · **horloge VPS/journal MT5 = UTC**.
Les bougies M5.hc sont horodatées en heure serveur ; converties en UTC ci-dessous.

---

## 1. Chronologie du gap (données)

Position fatale = **USDJPY LONG 1.73 lots** (deux tickets : 0.79 @ 161.801 résiduel du
25/06 ; 0.94 @ 162.565 ajouté au rebalance 01/07 22:05 Paris). Prix moyen 162.216, notionnel
173 102 $. Livre = 100 % J1 (w_jpy≈1.5, aucune autre jambe ouverte le 02/07).

Chemin USDJPY (bougies M5, open, heure **UTC**) et équité reconstruite (ancre 9927.07) :

| UTC | USDJPY open | équité | UTC | USDJPY open | équité |
|-----|-----|-----|-----|-----|-----|
| 04:00 | 162.455 | 10 181 | 06:30 | 162.254 | 9 968 |
| 05:00 | 162.430 | 10 155 | 06:35 | 162.215 | 9 926 |
| 05:30 | 162.409 | 10 133 | 06:40 | 162.220 | 9 931 |
| 06:00 | 162.331 | 10 050 | **06:45** | **162.209** | **9 920** |
| 06:05 | 162.264 | 9 978 | **06:50** | **161.795** | **9 477** (low 161.501 → 9 161) |
| 06:20 | 162.244 | 9 957 | 06:55 | 161.841 | 9 526 |

- **Début de baisse** : dérive lente 04:00→06:45 UTC (−25 pips en 2h45, position à l'équilibre,
  équité 10 180 → 9 920, jamais menacée).
- **Le saut mortel** : **bougie 06:45→06:50 UTC**. Open 06:45 = 162.209 ; open 06:50 = 161.795 ;
  **low intrabar 161.501**. Amplitude **≈ 50 pips (open→close), ~71 pips (jusqu'au low)** dans
  une seule bougie de 5 min.
- **Vitesse** : de 162.209 (06:45:00) à la clôture-force 161.717 (06:49:41) = **49 pips en
  4 min 41 s ≈ 10.5 pips/min** ; jusqu'au low ≈ 14 pips/min. Yen-buying violent (intervention
  BoJ/MoF suspectée).
- **Clôture (journal, UTC)** : `06:49:41.671 deal #154175818 sell 0.79 USDJPY @ 161.717` +
  `06:49:41.675 deal #154175819 sell 0.94 USDJPY @ 161.717`. Deux jambes, même prix, même
  seconde = **auto-liquidation serveur FTMO** (pas de fill EA dans fills.csv → EA n'a pas coupé).
- 07:36:32 UTC : compte basculé <ACCOUNT_ID> → 521090361.

---

## 2. Courbe d'équité & fenêtre du breaker

Niveaux (ancre 9927.07, position 1.73 lots) :
- **breaker_line 9577.07 ⇔ USDJPY 161.889**
- **daily_floor 9427.07 ⇔ USDJPY 161.749**
- clôture-force à 161.717 ⇒ équité **9 393** (< floor).

**La fenêtre où le breaker aurait pu s'armer sans breach = USDJPY [161.749 ; 161.889] = 14 pips
= équité [9427 ; 9577] = 150 $.**

À 06:45:00 UTC (dernière évaluation possible) l'équité était **9 920** — soit **32 pips
au-dessus** du seuil d'armement du breaker. Le prix a franchi les 14 pips de la fenêtre en
**~1 minute**, entièrement à l'intérieur de la bougie 06:45→06:50.

---

## 3. Preuve chiffrée : le breaker ne pouvait pas protéger

Le breaker EA (`InvariantCheckM5`, `book_executor.mq5:1082-1091`) n'est évalué **que sur la
grille M5** (`OnTimer:1499` — `p.min%5==0 && slot!=g_last_m5_slot`, « sémantique sim »).
L'EA tournait (watchdog `*/3` silencieux toute la nuit ⇒ heartbeat frais ; ticks.dat actif à
07:21 UTC ; `breaker_fired_today=0`). Donc c'est bien la **discrétisation 5 min**, pas une
panne, qui explique l'échec :

| Évaluation M5 breaker | Prix USDJPY | Équité | Action |
|---|---|---|---|
| **06:45:00 UTC** | 162.209 | 9 920 | rien (correct — 343 $ au-dessus du breaker) |
| *06:49:41 UTC* | *161.717* | *9 393* | **FTMO auto-close (moniteur continu)** |
| **06:50:00 UTC** | 161.795 | 9 477 | *aurait armé le breaker (9477<9577) et flatten @≈9477 → SURVIE* |

**Deux verrous, tous deux fatals :**
1. **Aucun cycle EA n'a pu observer une équité ∈ [9427, 9577].** Le seul « regard » pendant la
   bougie mortelle fut à 06:45:00 (équité 9 920, hors fenêtre par le haut) ; le regard suivant
   (06:50:00) tombe après le franchissement complet. **Le gap a sauté par-dessus la fenêtre du
   breaker.**
2. Même si l'on ignore (1), la prochaine évaluation M5 (06:50:00) serait arrivée **19 secondes
   trop tard** : FTMO, qui surveille l'équité en **continu**, a liquidé à 06:49:41. Le moniteur
   continu du prop-firm bat structurellement un breaker discret à 5 min.

Un breaker par-tick (au lieu de M5) se serait armé à 161.889 mais aurait flatten au marché en
plein flash → fill ~161.75-161.80 → équité ~9 450-9 480 → survie de justesse ; il réduit mais
n'élimine pas le risque (slippage du flash).

---

## 4. PnL décomposé

Compte $10 000. Ancre glissante 02/07 = **balance** 9927.07 (= 10 000 − 72.93 réalisé cumulé
au 01/07 ; l'équité 01/07 EOD 10 339 était balance + flottant positif). Swaps de la nuit
01→02/07 (USDJPY long, +) = **+5.84 $**, facturés AVANT la capture d'ancre (`DayRollover`
: `LogSwapsBilled()` puis ancre) ⇒ **déjà dans 9927.07**, hors perte du jour.

| Élément | Montant |
|---|---|
| Clôture 0.94 lot (162.565 → 161.717, −84.8 pips) | −492.91 $ (rapporté −494.44) |
| Clôture 0.79 lot (161.801 → 161.717, −8.4 pips) | −41.03 $ (rapporté −37.35) |
| **USDJPY réalisé total** | **≈ −533.9 $** |
| Autres jambes le 02/07 | 0 (US100/GER40 fermées le 01/07) |

Réconciliation : balance 9927.07 − ~532 ≈ **9 399.61** (équité de la snapshot post-breach). ✓
- **Perte du jour = −527.46 $ = −5.2 %** (dépasse le daily 5 % = 500 $) → **breach daily**.
- **DD total = 10 000 − 9 399.61 = −600.39 $ = −6.0 %** ; static floor 9000 (−10 %) **jamais
  approché** → **max loss NON atteint**. Confirme : c'est bien la limite **daily** qui a tué.
- L'écart −533.9 (calc) vs −527.46 (daily) ≈ prix de fill/spread/conversion exacts + le +5.84
  de swap déjà dans l'ancre.

---

## 5. vs distribution du sim (`…/cleanroom/engine.py`)

Le sim est **M5-discret** et évalue le bust/breaker par bougie (`engine.py:221-305`,
`hit_bust = eq_chk < lim_eff`, breaker au « M5 bar where equity < limit+30%×budget »). Sur CE
chemin :
- au bar 06:50 le sim voit un prix ~161.79 (open/close), équité ~9 477 **> floor 9 427**, et le
  breaker s'y déclenche ⇒ **le sim aurait enregistré une SURVIE**, pas un breach.
- le low intrabar 161.501 (équité 9 161) n'existe pas dans une évaluation par close M5.
- la seule provision « gap » du sim (`gap_stress`/`gap_k`, `engine.py:231-238`) n'amplifie que
  le **saut d'ouverture de journée** sur les jambes tenues — **pas un flash intraday** à 06:49.
- le sim ne modélise pas la **liquidation continue** du prop-firm.

**Verdict Q5 :** l'**amplitude** (0.5–0.7 yen) est dans l'échantillon historique (interventions
BoJ 2022/2024 bien plus grandes, deep_history 2007-2026). Mais le **mode de défaillance**
— traversée de la fenêtre [floor, breaker] à l'intérieur d'une bougie + liquidation continue FTMO
battant le breaker discret — est **hors-modèle**. Le sim **sous-estime structurellement** ce
tail. C'est l'analogue L19 (gap/slippage) côté prop-firm : le moniteur réel opère à une
résolution temporelle plus fine que la grille M5 supposée.

---

## 6. Leçons chiffrées (données rétrospectives → jugement prospectif)

Ce qui aurait borné la perte sur **ce gap précis** (perte USDJPY réalisée −533.9 $, daily −527) :

| Piste | Effet sur CE gap | Survit le daily 500 $ ? | Limite |
|---|---|---|---|
| **Plafond levier LCAP8 (≤8×)** | notionnel 173k→82k, perte ≈ **−254 $** | **OUI** (246 $ de marge) | un gap de 3 yen bust même à 8× (étude J1 : besoin ≤5.4×) |
| Cap ≤ 15.8× | perte ≈ −502 $ | limite | 16.80× réel = ~0 buffer de gap |
| Suspendre J1 en zone d'intervention (USDJPY élevé) | position non tenue → **0 $** | OUI | coûte le carry ; le plus robuste contre le tail intervention |
| SL de prix résidant @161.90 | fill ~161.7 (gap) → ~−449 $ | limite | peu fiable (traverse le niveau) ; **EA gelé de toute façon** |
| Breaker par-tick (vs M5) | flatten ~161.78 → équité ~9 470 | OUI de justesse | slippage flash ; ne bat pas la liquidation continue |

**Constat central :** la cause racine n'est pas le breaker (structurellement incapable sur un
flash intra-M5, cf. §3) mais le **dimensionnement**. Le livre tournait à **16.80×** de levier
notionnel sur un actif à risque d'intervention connu, avec **~zéro buffer de gap** (16.8× vs
seuil de survie 15.8× sur ce gap modeste). Les deux leviers déterministes et cohérents avec le
registre :
1. **LCAP8** (plafond levier ≤8× ; étude `j1_levcap_study`) — borne ce gap (−254 $) et divise
   par ~2 tout tail futur.
2. **Suspension J1 en régime d'intervention** — seule protection contre un vrai gap de plusieurs
   yens (que ni LCAP8 ni le breaker ne couvrent).

Un stop de prix et un breaker par-tick aident marginalement mais restent fragiles (fill de gap,
EA gelable). **La marge, pas la coupe, est le levier.**

---

### Annexe — position & rebalance (fills.csv, magic 220501)
25/06 BUY 1.80 @161.801 → 26/06 −0.01 → 29/06 −0.77 → 30/06 −0.23 (reste 0.79) ;
01/07 22:05 BUY 0.94 @162.565 → **1.73 lots**. `last_rebalance` snapshot : eq_used 10303.73,
scale 11.20, targets_usd USDJPY 173102.66. `breaker_fired_today=0`.
