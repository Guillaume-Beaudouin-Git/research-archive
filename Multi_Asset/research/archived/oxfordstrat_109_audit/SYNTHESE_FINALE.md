# Synthèse finale — Filtrage des 109 stratégies oxfordstrat sur l'univers FTMO

*Projet terminé : 109/109 traitées. `ftmo_lab.py` figé et inchangé (commit 9dea332) sur toute la campagne. 2026-06-07.*

---

## 1. Résultat global

| Verdict | N | Détail |
|---|---|---|
| 🟢 **KEEP** | **1 stratégie** (4 entrées registre #76-79) | **Ross Hook** (continuation de breakout court terme) |
| 🟡 **BORDERLINE** | **1** (#60) | **Oops Bullish** (gap-down-fade) — edge réel mais trop faible / non significatif en alpha sur données réelles |
| ❌ **DISCARD** | **100** | le reste |
| ⚪ **HORS-SCOPE** | **4** (#106-109) | études data (corrélations, vol clustering) — pas des stratégies |

**Taux de survie : 1/105 stratégies tradables (~1 %).** C'est le résultat attendu d'un filtrage rigoureux : la quasi-totalité des « patterns » publics sont du **beta déguisé**, des **artefacts de fill**, ou des **edges décayés**.

---

## 2. Le protocole (rappel)

Chaque stratégie reproduite fidèlement, passée par un pipeline **pré-enregistré et identique** :

1. **Gate 1 — délai+1** : l'edge survit-il à une exécution réaliste (open suivant) plutôt qu'au fill intrabar optimiste ? *(tue les artefacts de fill)*
2. **Gate 2 — two-sided** : les deux directions contribuent-elles ? *(tue le beta directionnel déguisé)*
3. **Gate 3 — DSR** : Sharpe significatif après déflation pour le multiple-testing ? *(tue le bruit de grille)*
4. **Gate 4 — OOS** : l'edge persiste-t-il train≤2015 / test≥2016 ?
5. **5ᵉ test — beta-apparié + mark-to-market** : bat-il un buy&hold apparié, en MTM réel et net du facteur tendance ? *(test décisif, ajouté après l'audit S012)*

Garde-fous appris en cours de route : **mark-to-market** obligatoire (le R étalé gonfle le Sharpe ×3, cf. correction #60) ; **facteur TSMOM** (distinguer alpha de la prime de tendance) ; **données réelles** (revalider hors proxy) ; **causalité par troncature** (anti-look-ahead).

---

## 3. Le survivant : Ross Hook (#76) — KEEP

Continuation de breakout court terme (achat de la reprise après la 1ʳᵉ correction d'un nouveau plus-haut). **Seule des 105** à franchir tout le protocole :
- 4 gates 0/4 ; **mark-to-market Sharpe ~0,7–1,0**, MaxDD réel −6 % ; **alpha t≈5** vs marché **+** facteur tendance (β≈0, corr TSMOM 0,11) ; **stable sur 3 sous-périodes dont 2019-2026** ; **causalité confirmée** (0 trade modifié par troncature) ; robuste aux coûts (+10 bps) et au délai d'entrée (+5 j).
- **Cadrage honnête** : ~60 % de l'edge = prime de breakout-momentum générique, ~40 % = sélectivité du hook. Réserves : retirer le forex, revalider les commodités sur données broker réelles, valider le slippage en paper.
- Livrables dédiés : `RAPPORT_INSTITUTIONNEL_S076_RossHook.pdf`, `SPEC_S076_ross_hook.md`, `AUDIT_DOSSIER_S076.md`, `s076_causality.py`.

---

## 4. Les « presque » — edges réels mais inexploitables

- **#60 Oops Bullish (BORDERLINE)** : gap-down-fade. Edge par trade réel (IC bootstrap > 0, même sur données FTMO réelles) mais, en MTM, **alpha couvert-beta non significatif** (t≈0,6 sur indices propres). Mon erreur initiale (Sharpe 3 par lissage) corrigée → ~0,7. Effet réel trop faible pour être exploité seul. Dossier : `AUDIT_DOSSIER_S060.md`.
- **#72/#73 RSI(2) Connors** : vraie mean-reversion, **alpha significatif 2000-2009** (Sh couvert 0,92) puis **décroissant** et **mort en 2019-2026** (t=−0,1). Cas d'école d'**alpha publié arbitré** (Connors 2009).

---

## 5. Taxonomie des échecs (ce qui ne marche pas, et pourquoi)

| Famille | Stratégies | Cause de rejet |
|---|---|---|
| **ORB-stop / Crabel** | NR, NR7, GSV, ORB, ORBP, Price-Breakout-NR7, Wide-Range (#55,56,37,61-65,67,68,96…) | **Artefact de fill intrabar** : le stop se remplit au pire prix ; délai+1 inverse l'edge |
| **Trend / momentum / MA** | KAMA, Aroon, Donchian, MACD, MTF, Hull, LR-slope, SMA, Vortex, Wilder, ZLMA, Livermore, Price-Momentum (#4-10,20-26,46-54,69,80,87,88,95,97,101,102…) | **Beta long déguisé** : le short perd, ne bat pas le buy&hold |
| **Fade de false-breakout** | False Breakout, Turtle Soup, Reversal Patterns, Wyckoff (#31,32,74,75,89,90,98-100) | **0 edge net** : win-rate faible non compensé, perd après coûts |
| **Bougies / patterns** | Doji, Engulfing, Hikkake, Hook, Smash Day (#16-19,27-30,41-45,81-85) | Pas de réversion exploitable / artefact de fill |
| **Exhaustion** | TD Sequential (#86,103-105) | Long-exhaustion légèrement positif mais short perd → net négatif |
| **Non reproductibles** | Pathfinder (T-bonds), Volume Filters (volume) (#66,92-94) | Instrument/donnée absent de l'univers FTMO CFD + edge nul/décayé à la source |
| **Saisonnalité / sorties** | Friday Momentum, Profit-Taking (#34,57,70,71) | Mort après coûts / cibles dégradent le résultat |

**Régularité de fond (2019+ everything-rally)** : tout système long-biaisé affiche un Sharpe récent ~1 via le seul beta. Le 5ᵉ test (beta-apparié) est ce qui sépare un vrai edge d'un beta — et c'est lui qui a recalé #60 et la quasi-totalité du cluster trend.

---

## 6. Données & limites du projet

- **Univers** : 30 CFD FTMO (10 indices *vrai OHLC type-FTMO 2000+*, 9 commodités *futures Yahoo proxy* sauf or, 9 forex *M1, courts*, 2 crypto). Coûts FTMO planchonnés par classe.
- **Limites assumées** : commodités en proxy (à revalider), forex courts/proxy, pas de volume (CFD), biais de sélection (univers d'aujourd'hui sur l'histoire), multiple-testing (109 stratégies → 1 survivant ; atténué par stabilité multi-période + données réelles sur le KEEP).

---

## 7. Livrables (repo `oxfordstrat_109`)

- `_INDEX.md` — registre maître des 109 verdicts (régénéré par `code/build_index.py`).
- `REPORT_S001…S109` — un rapport par entrée (spec, gates, verdict, repro).
- `code/ftmo_lab.py` — moteur + 4 gates, **figé** ; moteurs partagés (`orb_filtered`, `trend_lab`, `pricebreak`, `rosshook`, `smashday`, `turtlesoup`, `td_seq`, `wyckoff`, `beta_bench`).
- Dossiers d'audit approfondis : **Ross Hook** (PDF institutionnel + spec + causalité), **#60 Oops**, **#12 Bollinger**, re-audit complet des DISCARD.
- `results/` — gates + sensibilités + figures par stratégie.

---

## 8. Recommandation de clôture

**Un seul candidat mérite la suite : le Ross Hook (#76).** Étapes avant capital réel : (i) ré-implémentation indépendante (spec fournie), (ii) revalidation des commodités sur données broker réelles, (iii) paper-trading 3-6 mois (slippage des cassures), (iv) éventuelle simplification du hook (effet lent). Tout le reste est archivé comme **négatif rigoureux** — un résultat de recherche en soi : la grande majorité des patterns publics ne survivent pas à un protocole de coûts + fill réaliste + beta-apparié sur un univers CFD moderne.
