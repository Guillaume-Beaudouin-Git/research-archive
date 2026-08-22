# Skew research — session_vol_tail (candidats 1-5 : vol, structure & queue)
### Exploration 2026-06. Objectif : sleeves skew+ décorrélés pour portefeuille survie-propfirm (L7).
*Esprit : edge d'abord, barrières ensuite. Phase 1 généreuse. Skew négatif = drapeau, pas kill. Candidats-leçons NOMMÉS.*

---

## PHASE 1 — edge brut (sans coût, généreux). Gate : t>2 ET skew ≥ 0.

| # | candidat | signal nu | mean/j | hit | **skew** | t | SR | → P2 ? |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | VIX-term carry **timé** | short-vol si contango / long-vol si backwardation (VIXY) | +20bp | 58% | **−0,01** | +2,86 | 0,73 | ✅ oui |
| 1b | VIX short-vol nu | short-VIXY inconditionnel | +17bp | 59% | −1,66 | +2,40 | 0,61 | ⚠ skew− (le piège) |
| 2 | VRP | short-vol si VIX>réalisé | +17bp | 50% | **−1,70** | +2,59 | 0,66 | ⚠ skew− natif → mauvais profil |
| 3 | Dispersion | — | — | — | — | — | — | ⛔ **data-blocked** (IV options composants+indice non dispo gratuit) |
| 4 | Bond momentum | TLT TSMOM 60j (proxy daily) | ~0 | 49% | +0,16 | −0,07 | −0,01 | ✗ proxy sans edge ; **intraday Baltussen = data-blocked**, cf. actif `zn_baltussen` |
| **5-MR** | **reversal 1j SPX** | −sign(rendement veille) | +5,4bp | 52% | **+0,59** | **+3,61** | **0,70** | ✅✅ oui |
| 5-trend | trend 60j SPX | sign(rendement 60j) | +0,9bp | 52% | −0,17 | +0,57 | 0,11 | faible |

**Survivants Phase 1 :** #1 (VIX-term timé, skew neutre) et **#5-MR (skew positif +0,59)**. corr trend↔MR = **−0,15** (l'autocorrélation négative existe par construction).

## PHASE 2 — confrontation barrières (honnête, killante)

**#1 VIX-term timé — SURVIT.**
- **Coût (L33)** : robuste — SR 0,73→0,71→0,69→0,66 à 0/5/10/20 bp (turnover faible, régime contango persistant).
- **OOS (L31)** : 2011-18 SR 0,81 / 2019-26 0,59 — tient.
- **Skew** : −0,01 (neutre).
- **Archive** : "VIX term carry Sharpe 0,67 insufficient" (verdict edge existant). **Angle neuf = le timing term-structure neutralise le skew** du short-vol nu (−1,66 → −0,01). Ne re-prouve pas l'edge, caractérise le profil.

**#5-MR (reversal 1j) — positif mais FRAGILE.**
- **Coût (L33)** : SR 0,70→0,57→0,43→0,29 à 0/1/2/3 bp. Survit jusqu'à ~2-3bp (ES futures ~0,5-1bp OK).
- **Délai+1 (L26)** : SR **0,57 → 0,08** — s'effondre. Signal ultra-court ; **load-bearing = exécution immédiate au close**. Risque : artefact close-to-close (bid-ask bounce) non capturable. **Question ouverte : tester open→close vs close→close.**
- **Two-sided (L25)** : long-après-baisse SR **+1,11** vs short-après-hausse **+0,28** — deux côtés positifs (pas pur beta) mais **dominé par le dip-buying**.
- **OOS (L31)** : 2000-12 SR 0,76 / 2013-26 0,33 — **décaye** (cohérent McLean-Pontiff).
- **Archive** : short-term reversal indices = "décaye (L31)", MR deep-dive ~350 trials. **Décay confirmé, ne re-prouve pas. Angle neuf = le skew positif +0,59/+0,71** (l'archive jugeait sur Sharpe/décay, pas sur le profil de skew).

## PHASE 3 — aptitude portefeuille (le vrai critère : skew+ ET décorrélé)

Matrice de corrélation (2011-2026, n=3872) :

| | MR | TREND | VIXterm | LONG_EQ |
|---|---:|---:|---:|---:|
| **MR** | 1,00 | −0,13 | −0,06 | **+0,15** |
| TREND | −0,13 | 1,00 | +0,37 | −0,20 |
| VIXterm | −0,06 | +0,37 | 1,00 | **+0,26** |
| LONG_EQ | +0,15 | −0,20 | +0,26 | 1,00 |

| sleeve | SR (récent) | skew | corr LONG_EQ | corr autres | **sleeve complémentaire ?** |
|---|---:|---:|---:|---|---|
| **MR (reversal 1j)** | 0,21 | **+0,71** | +0,15 | ~0 partout | **✅ OUI** — skew+ ET décorrélé de tout (le profil exact recherché ; SR modeste OK, décorrélation > Sharpe) |
| VIXterm timé | 0,69 | −0,02 | **+0,26** | +0,37 au trend | ❌ **NON pour cet objectif** — SR fort mais skew neutre + beta equity + redondant au trend. Vrai edge, mauvais profil. |
| TREND 60j | 0,22 | −0,14 | −0,20 | — | ⚠ décorrélé equity mais skew− |

## VERDICT FINAL (session_vol_tail)

**Un seul sleeve complémentaire candidat : #5-MR (reversal 1j court-terme).**
- **skew +0,71**, **SR net ~0,21-0,43** (selon coût/période), **corrélation ~0 aux autres sleeves et +0,15 au beta equity**, **statut archive = edge décayé connu, mais le profil skew+ est l'angle neuf non documenté.**
- **Caveat bloquant à lever avant phase exécution** : le délai+1 s'effondre (0,08) → valider que le reversal est capturable en open→close (pas un artefact de close-print). Sans ça, non-déployable.

**Écartés :** VIXterm (skew neutre + beta equity, bon edge mauvais profil) ; VRP (skew −1,70 natif, le piège) ; Bond (intraday data-blocked → `zn_baltussen`) ; Dispersion (data-blocked options).

## Candidats-leçons (NOMMÉS, pas numérotés — numéro tranché au merge)
- **« Timing term-structure neutralise le skew du short-vol »** — le carry VIX nu a skew −1,66 ; timé long-vol en backwardation → −0,01 avec edge intact (t 2,86).
- **« Skew = dimension de sélection distincte du Sharpe »** — l'archive jugeait VIX-term/reversal sur Sharpe/décay ; le profil de skew (signe, concentration) est un critère portefeuille orthogonal, à caractériser même sur des edges archivés.
- **« Reversal court-terme : skew+ mais load-bearing = exécution au close »** — le délai+1 le tue, drapeau exécution (close-print vs capturable).

---
*session_vol_tail, candidats 1-5. Données : Yahoo (^VIX, ^VIX3M, VIXY, ^GSPC, TLT) ; tout backtest, 0 jour live. Réconcilié contre l'archive (VIX-term, VRP, reversal = connus ; angle neuf = skew). Ne touche pas aux autres sessions ni overnight_research/.*
