# J1 — USDJPY carry-aligned trend (ledger canonique)
### Première stratégie du projet trend-following. Conforme à `CHARTE_methodo_trendfollowing.md`.

> **TL;DR — Premier VRAI edge robuste de tout le travail FTMO** : Sharpe 0,58, CI95 [+0,18, +0,96], **stable entre régimes**, **cost-robuste** (spread FX serré + swap positif). **Verdict exact (revu équipe) : beta-dominant + alpha résiduel marginalement significatif, non hedgé** — J1 ≡ long-only USDJPY, **R²=0,51** sur ce beta (~49 % de variance non expliquée), **alpha résiduel +2,1 %/an, t=1,95-1,98**. Ni "pur beta", ni un alpha à sur-vendre. **Mais p(pass) FTMO 2-step = ~33 % = le mur** (la barrière domine, pas le signal). **Skew : voir §3.5 — le prior "carry-crash / skew négatif structurel" est FALSIFIÉ.**

---

## 1. Spécification (signal à T-1, trade à T)
- **Instrument** : USDJPY daily (Yahoo, 2000-2026, 6857 j ; 3 glitches Yahoo nettoyés → pire jour réel −5,1 %, vol 9,8 %).
- **Trend** : TSMOM 12-1 (signe rendement 12 mois hors dernier mois) — Moskowitz et al., lookback **non tuné** (littérature).
- **Carry** : différentiel taux US-JP (proxy ^IRX US 13-sem − BoJ ~0, lift-off 2024+), laggé 2 j. **Carry > 0 sur 100 % de la période** (US > JP toujours) → le filtre carry-aligned = **long-only de facto**.
- **Sizing** : vol-target 10 % ann (vol laggée 20 j), cap levier 3.
- **Coût** : spread 0,6 bp/RT ; **swap = +carry/252 sur la position** (l'avantage structurel USDJPY).

## 2. Résultats incrémentaux (≤3 mods)
| variante | Sharpe | MaxDD | skew | ann |
|---|---:|---:|---:|---:|
| base trend (swap off) | 0,35 | −36 % | −0,24 | +3,9 % |
| + swap (carry encaissé) | 0,42 | −37 % | −0,24 | +4,7 % |
| **+ filtre carry-aligned** | **0,58** | **−23 %** | −0,29 | +4,6 % |

## 3. Validation (charte)
- **Bootstrap CI95 Sharpe** : [+0,18, +0,96] → exclut 0, edge réel. t-stat +2,05, p(SR>0)=0,98.
- **Stabilité régime** : 2000-2012 SR +0,53 / 2013-2026 SR +0,63 → **stable** (≠ ORB/lundi régime-concentrés). ⭐
- **Coût** : spread FX serré (~0,6 bp) + **swap positif** → survit même ×2 coût. **Pas de falaise L33** (contraste fort avec l'ORB).
- **Décomposition beta/alpha (exacte)** : J1 ≡ long-only USDJPY vol-targeté → régression sur ce beta : **R²=0,51, alpha résiduel +2,1 %/an, t=1,95-1,98**. Donc **beta-dominant + alpha résiduel marginalement significatif, non hedgé** — ~49 % de variance non expliquée par le passive long.

### 3.5 FALSIFICATION — le prior "carry-crash / skew négatif structurel" est FAUX
Hypothèse posée en amont (à tort) : "USDJPY = devise de portage → skew négatif structurel, les pires jours sont des unwinds risk-off (2008/2020/2022)." **Falsifiée par les données :**
- **Skew quotidien −0,29 mais skew MENSUEL +0,70** (équipe : +0,31 — *magnitude à aligner au merge, le SIGNE positif tient des deux côtés*). Le négatif quotidien est du bruit micro-structure, PAS structurel — à l'horizon de détention, J1 a un skew **positif** (convexité trend classique).
- **Les 10 pires jours de J1** tombent en 2002, 2005, 2007, 2015, 2019, 2022, 2024, 2026 — **1/10 en 2008/2020/2022** (équipe : 0/10 — *à aligner au merge, la conclusion "pas de cluster crise" tient des deux côtés*). Ils **ne clusterisent PAS dans les crises** → pas de carry-crash.
- **Conséquence** : la "modif skew par trailing-stop" (testée → échec) répondait à un problème **inexistant**. C'est un résultat utile : un prior corrigé.

## 4. p(pass) FTMO 2-step (full-sample, cap 6 mois)
| sizing/j | p(pass) | bust | médiane |
|---|---:|---:|---:|
| 1,0 % | 23 % | 33 % | 3,5 mo |
| **1,5 %** | **33 %** | 52 % | 2,5 mo |
| 2,0 % | 30 % | 66 % | 1,8 mo |

→ **Plateau ~33 % = ORB = mur barrière.** Plat selon le sizing (canonique : régime/edge-déterminé, pas sizing).

## 5. Verdict
**J1 = beta-dominant (R²=0,51 sur long-USDJPY) + alpha résiduel marginal non hedgé (+2,1 %/an, t=1,95-1,98).** Réel, robuste, régime-stable, cost-robuste — mais **ne bat pas le mur FTMO ~33 %** car (a) Sharpe 0,58 ≪ ~1,4 requis, (b) la barrière domine.

**Non-déployable / dilutif — verdict reformulé sur chiffres soutenables (pas de SR_port agrégé) :** J1 = sleeve **beta-proxy** (corr +0,71 au passive long-USDJPY, R²=0,51), **SR_net 0,58 — sous le gate 0,7 ET sous la composante G1 (~0,69)**. Ajouter un sleeve beta-overlappant à SR inférieur au gate **n'améliore pas un book dont les composantes ont un SR supérieur → dilutif par construction.** *Conclusion établie sur le SR du sleeve seul + le beta-proxy ; le SR_port 2,31/2,36 d'une revue parallèle n'a PAS été reconstruit proprement et n'est pas requis.* Le skew n'est PAS un facteur négatif (§3.5).

## 6. Implication stratégique — le vrai levier du trend-following
Un seul actif TF = Sharpe ~0,5 → mur. **Le pouvoir du trend-following est la DIVERSIFICATION cross-asset** (résultat CTA / Moskowitz-Ooi-Pedersen) : ~5 sleeves TF décorrélés à 0,5 chacun → **book Sharpe ~0,5×√5 ≈ 1,1**, ce qui remonterait le p(pass) vers ~45-50 %. **Et** un book gold/oil/crypto (skew TF positif) **compense le skew négatif de l'USDJPY**.
→ **Next : construire G1 (or) + 2-3 sleeves, mesurer le book diversifié.** C'est le seul chemin TF qui peut bouger le mur — mais honnêtement, même Sharpe 1,1 plafonne ~45-50 % en 2-step (mur Sharpe), donc viser le book pour un déploiement *personnel/CV* ou une firme à meilleure structure, pas un miracle FTMO.

---
*Ledger J1 2026-06-03. Données : `outputs/usdjpy_clean.parquet`. Backtest, 0 jour live. Sharpe net coût, swap modélisé, bootstrap CI, régime-split.*
