# Skew research — session_E2_seasonal_book (grains/softs + book saisonnier standalone)
### Exploration 2026-06. La mort du moteur (session_F, L36) ouvre : un book SAISONNIER SEUL clear-t-il +10% phase-1 ?
*Cadre : seules 2 structures clearent le carry overnight FTMO — (A) intraday-flat, (B) prime >> carry-sur-notionnel. session_E a prouvé (B) avec précieux-Q1. Ici : étendre (B) aux grains + tester le book (B)-seul.*
*Règle : GATE-0 contango EN PREMIER (piège session_B/UNG), puis net-CFD (L33), two-sided (L25), OOS (L31), DSR déflaté month-selection, corr-précieux (additionnalité). Pas de baseline de-levée (L19).*

> **Dédup** : précieux-Q1 vient de `session_E` (silver/platinum Jan) + `session_B` (gold Jan). Cité, non re-prouvé.

---

## PARTIE 1 — Grains/softs

### GATE-0 contango/roll (le piège session_B, AVANT toute claim) — TOUS PASSENT
| grain | drift annualisé | mois négatifs | GATE-0 |
|---|---:|---:|---|
| COFFEE | +4,5%/an | 4/12 | ✅ pas de bleed |
| COCOA | +4,8%/an | 4/12 | ✅ pas de bleed |
| SOYBEAN | +3,7%/an | 4/12 | ✅ pas de bleed |
| WHEAT | +3,3%/an | 5/12 | ✅ pas de bleed |
| CORN | +3,6%/an | 4/12 | ✅ pas de bleed |

Les séries `commod_daily` grains ne saignent PAS le contango (drift positif, mois mixtes) — contraste UNG (−453bp roll, ~12/12 négatifs, session_B). **Gate-0 n'est pas le killer ici** ; le net-CFD l'est.

### NET-CFD par grain (mois pré-spec mécanisme, swap grain −5bp/nuit×21 + spread)
| grain | mois (mécanisme) | gross (t) | **NET (t)** | skew | corr-préc | OOS | DSR×12 | verdict |
|---|---|---|---|---:|---:|---|---:|---|
| COFFEE | Jul (gel Brésil) | +181bp (1,99) | +66bp (0,73) | +0,55 | −0,00 | +145/+214 | 0,34 | ❌ meurt |
| WHEAT | Mai (winter-wheat) | +241bp (1,69) | +126bp (0,89) | +0,72 | −0,00 | +226/+254 | 0,29 | ❌ meurt |
| COCOA | Sep (pré-récolte) | −130bp (−0,72) | −245bp | −0,26 | +0,00 | +150/−385 | 0,01 | ❌ meurt |
| SOYBEAN | Jul (pod-fill) | −275bp (−2,81) | −390bp | +0,50 | +0,00 | −183/−359 | 0,00 | ❌ meurt |
| CORN | Jun (pollinisation) | −232bp (−1,89) | −347bp | +0,68 | +0,00 | −290/−158 | 0,00 | ❌ meurt |

**0 grain survit.** Deux familles d'échec :
1. **Coffee (Jul +181bp t=1,99) et Wheat (Mai +241bp t=1,69) ont un VRAI seasonal positif, OOS-stable** — mais (a) le **swap grain lourd (~−115bp/mois)** les ramène à t<1, et (b) le **DSR×12 (0,34/0,29) les tue sur la sélection-de-mois**, indépendamment du swap. Double mort.
2. **Soybean (Jul), Corn (Jun), Cocoa (Sep) sont wrong-signed** : juin/juillet sont des **sommets saisonniers** (la prime météo est intégrée plus tôt et se dénoue), pas des creux longs. Mon pré-spec directionnel était faux ; je ne re-mine pas (best-month ≠ mon mois pour les 5 → discipline anti-mining tenue, DSR×12 = 0,00-0,01).

→ **Contraste précieux vs grains** : silver-Jan gross +468bp >> swap, survit net t=3,07 ; coffee/wheat gross +180-240bp < (swap + déflation DSR×12). **Le précieux survit parce que sa prime est 2-3× plus grosse que le hurdle ; les grains non.** corr-précieux ≈ 0 partout (auraient été additifs s'ils survivaient — mais ils meurent).

## PARTIE 2 — Book saisonnier SEUL : +10% phase-1 sous le cap ?
Book = précieux-Q1 seul (grains morts). Sleeve = EW(silver, platinum, gold) **vol-target 10%/leg**, net swap, **janvier uniquement**, flat le reste.

> **Réalité déployable** : à vol-target disciplinée, le sleeve fait **+1,12%/janvier (±2,03%)**, PAS +387bp (ça = spot silver brut, vol ~25%). Worst single day −3,48%. Il ne tire qu'**~21 jours/an**.

**MC FTMO phase-1** (+10% target, −10% total, −5% jour ; circuit-breaker −3%/jour + per-sleeve vol cap ; sans limite de temps, on empile les Januaries) :

| levier | p(pass) | breach −5%/jour | #Januaries médian | vol/janvier |
|---:|---:|---:|---:|---:|
| L=1 | 99,7% | 0,0% | **8** (≈8 ans) | 2,0% |
| L=2 | 93,1% | 4,0% | 3 | 4,1% |
| L=3 | 77,5% | 16,7% | 2 | 6,1% |
| L=4 | 69,5% | **25,4%** | 1 | 8,1% |
| L=6 | 63,9% | **36,1%** | 1 | 12,2% |

### Décomposition bust — la tension structurelle
- **À levier sûr (L=1) : 99,7% pass mais 8 Januaries = 8 ans.** La fenêtre tire 1 mois/an à ~+1,1% → +10% exige ~9 ans d'empilement. Sans limite de temps c'est « lent », pas « bust » — mais inutilisable comme standalone.
- **À levier pratique (L≥4, +10% en 1 janvier) : 25-36% de breach −5%/jour = bust FTMO instantané.** Le worst-day du sleeve (−3,48% à L=1) devient −14% à L=4 → le cap journalier saute.
- **Le levier requis pour un +10% pratique EST le risque.** Il n'y a pas de « sweet spot » : entre L=1 (8 ans) et L=4 (25% bust), L=2-3 donne 2-3 ans ET 4-17% de breach — médiocre des deux côtés. **La cause = sparsité** : 1 fenêtre/an ne *stacke* pas (pas de chevauchement temporel pour construire le rendement sans levier). Les grains auraient densifié le calendrier → mais ils meurent net-CFD.

## VERDICT FINAL (session_E2)
**(1) 0 grain/soft survit net-CFD** — gate-0 passe (pas de bleed), mais le swap grain lourd + DSR×12 tuent même les vrais seasonals (coffee/wheat). Le précieux-Q1 reste le SEUL seasonal net-survivant.

**(2) Le book saisonnier-SEUL n'est PAS un standalone FTMO viable — structure (B) trop éparse.** Soit 8 ans (L=1, sûr mais inutile), soit cap-breaching (L≥4, 25%+ bust). La prime (B) est réelle et net-survivante, mais **1-2 fenêtres/an ne stackent pas assez** pour +10% à un levier qui survit au cap journalier.

→ **Implication arc** : moteur mort (F) + (B) trop éparse pour standalone ⇒ le précieux-Q1 est un **topping décorrélé skew+** à poser SUR une structure (A) intraday-flat qui porte le gros du +10%, **pas** un book autonome. La densité temporelle doit venir de (A) ; (B) ajoute du rendement décorrélé sans porter la barrière seul.

## Candidats-leçons (NOMMÉS)
- **« Gate-0 contango passe pour les grains ; le killer est le swap + DSR×12, pas le roll »** — drift +3 à +5%/an (pas de bleed UNG) mais coffee/wheat (+180-240bp gross réels) meurent au swap grain (~−115bp/mois) ET à la déflation month-selection (DSR×12 0,29-0,34). Le piège session_B (roll) n'est pas universel ; vérifier les DEUX.
- **« Prime saisonnière survit net-CFD seulement si 2-3× le hurdle »** — précieux +468bp >> ~81bp survit (t3,0) ; grains +180-240bp < (swap+DSR) meurent. Le ratio prime/hurdle, pas la significativité brute, décide.
- **« Structure (B) [prime saisonnière] est trop éparse pour un standalone FTMO »** — 1 fenêtre/an, +1,1%/an à vol-target sûre → +10% = 8 ans (L=1) ou 25% bust (L=4). Les fenêtres ne stackent pas ; (B) est un topping sur (A), pas un book autonome.
- **« Vol-target disciplinée ≠ headline spot »** — silver-Jan +387bp brut devient +1,1%/Jan EW vol-targeté 10%. Toujours dimensionner la prime à la vol cible avant de raisonner p(pass), pas au notionnel spot.
- **« Mois pré-spec wrong-signed : ne pas re-miner »** — soybean/corn juin-juillet = sommets, pas creux (gross négatif) ; best-month ≠ mon mois → je rapporte l'échec, je ne sélectionne pas a posteriori (DSR×12 0,00 confirme qu'il n'y a rien à sauver).

---
*session_E2_seasonal_book. Données : commod_daily (Ag/Pt/Au/coffee/cocoa/soybean/wheat) + xs_universe (corn), daily 2005-2026. Swap modèle conservateur (grains −5bp/nuit ; métaux −3,5). HAC lag-6, DSR déflaté Bailey-LdP ×12, MC 20k paths. Tout backtest, 0 jour live. Réconcilié archive (session_E précieux, session_B or/UNG, session_F moteur mort — pas de re-preuve). Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/. Dédup vs session_E/session_B flaggé.*
