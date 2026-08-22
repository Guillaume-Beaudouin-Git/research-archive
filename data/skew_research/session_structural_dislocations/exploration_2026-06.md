# Skew research — session_structural_dislocations (candidats 1-5 : contraintes & dislocations structurelles)
### Exploration 2026-06. Objectif : sleeves skew+ décorrélés pour portefeuille survie-propfirm (L7).
*Esprit : edge d'abord, barrières ensuite. Phase 1 généreuse. Skew négatif = drapeau, pas kill. Candidats-leçons NOMMÉS.*
*Skew mesuré à l'**HORIZON DE DÉTENTION**, pas daily. Délai+1 / look-ahead testés dès Phase 1.*

> ⚠ **Chevauchement archive** : ce batch re-tread en partie le **BATCH 2 de `session_3`** (« Flux & contraintes mécaniques ») et l'actif `cip_eoq`. Réconcilié ci-dessous, pas re-prouvé. À déduper au merge.

---

## PHASE 1 — edge brut (sans coût, généreux). Gate : t>2 ET skew(horizon) ≥ 0.

| # | candidat | testabilité | signal nu | n | mean | skew_horiz | t | SR | corrEQ | gate |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | reconstitution → flux ETF sectoriel | ⛔ archive+data | — | — | — | — | — | — | — | ✗ **session_3 B2** |
| 2 | VIX expiry mercredi (SOQ) | ⚠ proxy daily | long VIXY day-after-expiry | 182 | +54,9bp | **+1,43** | +1,76 | +2,07 | ~0 | ⚠ **near-miss** (tradeable t<2) |
| 3 | cross-currency basis quarter-end | ⛔ archive+data | — | — | — | — | — | — | — | ✗ **cip_eoq KILL** |
| 4 | dividend futures / ex-div | ⛔ data | — | — | — | — | — | — | — | ✗ data-blocked |
| 5 | leveraged-ETF EOD rebalance | ✅ NQ 1-min | sign(open→15:30)·r_last30, jours gros move | 1172 | +1,58bp | **+0,78** | +1,28 | +0,59 | −0,05 | ⚠ **near-miss** (t<2) |

**Survivants Phase 1 (gate strict t>2) : AUCUN.** Mais **#5 et #2 sont des near-miss au PROFIL exact recherché** (skew+ ET décorrélation natifs) — le vrai edge vit en **intraday**, que le daily/proxy sous-estime. Distincts des échecs plats du batch cross-asset.

### Détail / robustesse

**#5 — leveraged-ETF EOD rebalance : mécanisme réel, edge sous-puissant + 1 LOOK-AHEAD attrapé.**
Signal propre = `sign(open→15:30)·r_last30` (connu à 15:30, trade 15:30→16:00, zéro look-ahead).
- uncond : mean +0,57bp, t=1,15, SR 0,29, skew_horiz +0,54, corrEQ −0,03.
- **conditionnel jours gros move** (flux lev-ETF ∝ |move|) : mean monte **monotone** +1,13→+1,58→+1,73bp aux déciles |move|≥Q50/Q70/Q90, SR 0,47/0,59/0,48 — **la signature économique est correcte** (l'effet croît avec la taille du move). MAIS t plafonne ~1,3 (jamais >2 ; r_last30 std 31bp noie un edge de 1-1,7bp/trade). Net de ~0,5bp coût NQ → SR ~0,4. **Sous-significatif.**
- 🚩 **LOOK-AHEAD ATTRAPÉ** : la variante `sign(r_first30+r_rest)·r_last30` sortait **t=12,22 / SR=3,10 / skew +2,57** — FAUX. Vérif décomposition : `corr(r_rest, r_rth−r_first30) = +1,000` → **`r_rest` inclut `r_last30`**, donc le signal prédisait r_last30 par lui-même. Écarté. (**3e prise de look-ahead du projet** : trailing-stop 2,05→0,32, gap-fade, lev-ETF 3,10→1,15. Pattern confirmé : t spectaculaire = audit artefact, 3/3.)
- 🛑 **VERDICT ACTÉ — DIFFÉRÉ AU SORT DE L'ORB.** Edge INTRADAY sous le gate → retombe sur le **tueur n°1 de l'ORB : coût d'exécution intraday non mesuré**. Un edge intraday *déjà* sous le gate qui devrait *en plus* survivre au coût intraday = **très improbable** (l'ORB, à t plus haut, n'y arrive déjà pas). **Ne pas investir de cycles.** À reprendre SEULEMENT si la mesure de coût intraday (ORB 15h30) revient favorable — partage le sort de l'ORB, attend le même verdict de coût.

**#2 — VIX expiry mercredi (SOQ) : effet réel sur spot, sous-significatif sur l'instrument tradeable.**
VIX se règle par auction SOQ le mercredi 30j avant le 3e vendredi du mois suivant. Vol supprimée dans l'auction, rebond après :
- **spot ^VIX** (propre, sans split) day-after-expiry : **+120bp, t=2,02** (vs baseline +22,8bp). Effet daté réel.
- **VIXY tradeable** day-after : +54,9bp, **t=1,76**, skew **+1,43** (long-vol = skew+), décorrélé. Plus faible que le spot = **dampening des futures + contango** (cf. L23b : mesurer l'instrument tradeable, pas l'indice).
- V-shape (after−before) spread +90bp mais t=1,16 (NS). Day-before/day-of NS.
- **Verdict** : profil idéal (skew+1,43, décorrélé, événement mensuel ~12/an) mais **t=1,76 < 2 sur le tradeable**, et le **daily ne capture pas l'auction intraday** (le vrai edge est le print SOQ, pas le close-to-close).
- 🛑 **VERDICT ACTÉ — NON-FTMO + DIFFÉRÉ.** VIXY/produits vol = **ETF = perso-only (Gate-0 FTMO)**, comme le month-end bond rally. **Pas FTMO-tradeable**, point. Le suivi intraday vol n'est pertinent que pour un livre **personnel**, et même là il partage le sort de l'ORB (coût intraday non mesuré). **Ne pas investir de cycles** avant que le verdict de coût intraday ORB revienne favorable.

### Réconciliation archive (#1, #3, #4 — cités, non re-prouvés)
- **#1 reconstitution** → `session_3` **BATCH 2 / B2** : ❌ NON-APPLICABLE — « l'indice rebalancé est net ≈0 ; pas de dates recon ; érodé par l'anticipation ; sur CFD d'indice = négligeable ». L'angle « flux ETF sectoriel » n'y échappe pas : (a) dates de reconstitution non dispo gratuitement, (b) ETF sectoriels **non-tradeables FTMO**. Re-tread.
- **#3 cross-currency basis quarter-end** → `Forex/research/active/cip_eoq` : **KILL confirmé** — μ net 1-3bps ≪ 3×coût 24bps (L11 ×5) ; forwards observés indisponibles (CME XEURBI, EUR/USD 3M fwd, EURIBOR/LIBOR 3M tous discontinués/payants). Seul un **proxy spot quarter-end** serait testable (≠ le basis) — hors-scope, l'edge documenté est nul net.
- **#4 dividend futures / ex-div** → adjacent `session_3` **B4** (NAV arb : ❌ besoin NAV intraday + ETF non-tradeables). Dividend futures = **aucune data gratuite**, effet petit. Data-blocked.

## PHASE 2 / 3 — sans objet (gate strict)
0 survivant à t>2 → rien à confronter aux barrières ni à corréler.

## VERDICT FINAL (session_structural_dislocations) — ACTÉ
**0 survivant FTMO-tradeable.** Les dislocations structurelles produisent **le bon PROFIL** (skew+ et décorrélation *natifs* : long-vol day-after-VIX-expiry skew +1,43 ; lev-ETF EOD skew_horiz +0,5→+1,1, corrEQ ~0) — **mais** :
- **3/5 data/archive-bloqués** : reconstitution (`session_3 B2`), basis CIP (`cip_eoq` KILL), dividend futures — données propriétaires ou instruments non-FTMO.
- **2/5 near-miss intraday qui retombent sur le sort de l'ORB :**
  - **#5 lev-ETF EOD** : edge intraday *déjà* sous le gate (t=1,15) → devrait *en plus* survivre au **coût d'exécution intraday non mesuré** = le tueur n°1 de l'ORB. Très improbable (l'ORB, à t plus haut, échoue déjà). 
  - **#2 VIX-expiry** : VIXY/produits vol = **ETF = perso-only (Gate-0 FTMO)**, comme le month-end bond. Non-FTMO-tradeable.

**→ Near-miss intraday + faibles + terrain coûteux/non-FTMO = profil ORB en moins bon. Ne pas investir de cycles.** Les deux sont consignés au registre comme **« edges intraday potentiels, sous-puissants en daily, à reprendre SEULEMENT si la mesure de coût intraday (ORB 15h30) revient favorable »** — ils partagent le sort de l'ORB et attendent le même verdict de coût. #2 reste de toute façon perso-only (Gate-0 FTMO).

## Candidats-leçons (NOMMÉS, pas numérotés — tranché au merge)
- **« t spectaculaire = audit artefact obligatoire (3/3) »** — look-ahead par somme de sous-périodes : `r_rest` incluait `r_last30` (`corr=+1,000`) → `sign(somme)·r_last30` prédit r_last30 par lui-même, t=12,2 FAUX vs 1,15 propre. **3e prise du projet** (trailing-stop 2,05→0,32, gap-fade, lev-ETF 3,10→1,15) : un t/SR spectaculaire déclenche systématiquement un audit. Vérifier la décompo additive (`r_rth = r_first30+r_rest+r_last30` ?) avant tout signal-somme de buckets.
- **« Near-miss intraday partage le sort de l'ORB »** — un edge intraday *déjà* sous le gate daily (t<2) ne survivra quasi jamais *en plus* au coût d'exécution intraday (le tueur n°1 de l'ORB, qui échoue déjà à t plus haut). Ne pas dépenser de cycles : différer au **verdict de coût intraday ORB 15h30** ; reprendre seulement s'il revient favorable. #5 lev-ETF en est le cas-type.
- **« Produits vol / ETF = Gate-0 FTMO (perso-only) »** — VIXY et tout produit vol/ETF ne sont **pas FTMO-tradeables** (même classe que le month-end bond rally). Classer la FTMO-tradeabilité **au pré-flight**, avant de mesurer un edge — un beau profil skew+ sur un instrument Gate-0 reste hors-challenge.
- **« Dislocation structurelle = bon profil, edge intraday/non-FTMO »** — #5 et #2 ont skew+ ET décorrélation natifs (le profil L7 voulu) mais l'edge réel est intraday (auction SOQ, flux EOD gros move) et/ou sur instrument non-FTMO. Le daily caractérise le profil, pas la puissance ; le profil seul n'est pas allouable.
- **« VIX non-tradeable ≠ VIXY tradeable »** — day-after-expiry +120bp t=2,02 sur spot ^VIX mais +55bp t=1,76 sur VIXY (dampening futures + contango). Mesurer l'instrument tradeable, pas l'indice (L23b).
- **« Dislocations à data propriétaire = mur récurrent »** — reconstitution (dates recon), basis CIP (forwards observés), dividend futures : 3/5 exigent des données payantes ou des instruments non-FTMO. Archive `session_3 B2/B4` + `cip_eoq` le confirment ; pré-flight data avant tout calcul.

---
*session_structural_dislocations, candidats 1-5. Données : NQ 1-min 2010-2026 (databento, local) + nq_intraday_panel ; Yahoo ^VIX/VIXY (réseau OK). Tout backtest, 0 jour live. Réconcilié archive (session_3 B2/B4, cip_eoq KILL — pas de re-preuve). Phase 1 seulement. Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/.*
