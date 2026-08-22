# Mémo de déploiement — Book Trend J1+G1
### Le vrai actif du projet. Framing strictement 1 SEUL ESSAI (jamais de % multi-essais).

> **TL;DR — Le pivot trend-following a produit le seul résultat réel du projet : un book de 2 edges time-series robustes, décorrélés, cost-robustes (Sharpe ~0,72). C'est un actif quant déployable (perso/CV/GitHub). Sur FTMO 2-step, 1 essai = ~33-36 % — la meilleure proba honnête du projet, mais sous un passage confortable. Le mur ~35 % est structurel (quadruple-confirmé : breakout, trend, cross-sectional, structure de firme).**

---

## 1. Les deux sleeves (vrais edges, validés charte)

| sleeve | spec | Sharpe (full/récent) | skew | swap | validation |
|---|---|---:|---:|---|---|
| **J1** USDJPY | TSMOM 12-1 carry-aligned (long-only de facto, carry>0 toujours) | 0,58 / 0,49 | −0,29 | **+** (carry) | CI95 [+0,18;+0,96], stable 2 régimes, cost-robuste |
| **G1** Gold | TSMOM 12-1 | 0,69 / 0,54 | −0,16 | − (funding) | + sur 3 décennies, cost-robuste |

**Book equal-risk : corr +0,02, Sharpe 0,72, skew −0,36.** Décorrélation parfaite, vrais edges (≠ ORB qui mourait au coût).

> **Nature exacte de J1 (revue équipe) : beta-dominant + alpha résiduel marginal non hedgé.** J1 ≡ long-only USDJPY → R²=0,51 (corr +0,71), **alpha résiduel +2,1 %/an, t=1,95-1,98**. Ni "pur beta", ni un alpha à sur-vendre.
> **Dilutif / non-déployable — sur chiffres soutenables :** J1 SR_net **0,58 < gate 0,7** ET **< composante G1 (~0,69)** ; sleeve beta-overlappant à SR inférieur → **dilutif par construction**. *Verdict établi sur le SR du sleeve + le beta-proxy, PAS sur le SR_port 2,31/2,36 (revue parallèle, non reconstruit, écarté).*

## 2. p(pass) — 1 SEUL ESSAI (le seul cadre)

| structure | 1 essai (full) | 1 essai (récent) |
|---|---:|---:|
| **FTMO 2-step** (daily 5 %, static 10 %) | **36 %** | **33 %** |
| 1-step trailing 6 % (futures prop réaliste) | 36 % | 35 % |
| 1-step no-daily static 10 % (firme inexistante) | 62 % | 59 % |

→ **Sur toute firme réelle : ~33-36 % en 1 essai.** Sizing : **floor-taper c≈0,20** (maîtrise le bust sans monter le plafond — le sizing n'est pas le levier, L35). Le 62 % exige une firme static-large-no-daily qui n'existe pas (canonique #1).

## 3. Verdict honnête (1 essai)

- **Le book ne passe pas confortablement FTMO en 1 essai (~35 %).** C'est la meilleure proba réelle du projet, mais c'est sous 50 %. Le mur est structurel : barrière × Sharpe ~0,5-0,7 (plafond des edges retail robustes). >60 % en 1 essai exigerait Sharpe ~1,4 — inexistant en price-pattern retail.
- **La vraie valeur du book n'est PAS FTMO** — c'est un **actif déployable** où la contrainte "passer en 1 essai" ne s'applique pas : book personnel (vrais edges décorrélés), ligne CV/GitHub (rigueur + honnêteté = ce qui fait un bon quant).

## 4. Pré-déploiement (charte)

- **Mesurer les swaps réels** (J1 + / G1 −) sur démo avant capital — le coût décide (L33). Données rates = proxy ^IRX à durcir.
- **0 jour live** → paper ≥3 mois, réconcilier slippage/swap.
- **Skew — prior FALSIFIÉ (revue équipe)** : "skew négatif structurel / carry-crash" sur J1 est **faux**. Skew J1 **mensuel +0,70** (positif ; le −0,29 quotidien est du bruit micro-structure), et les 10 pires jours **ne clusterisent PAS** dans 2008/2020/2022 (1/10). Le book a un skew quotidien −0,36 mais ce n'est PAS un carry-crash. La modif trailing-stop (échec) répondait à un problème inexistant. *Falsification = un des résultats utiles.*
- **Régime** : Sharpe stable mais p(pass) régime-dépendant ; pas de timing du départ (bruit blanc).

## 5. Ce qui est banké (au-delà du book)
La **charte méthodo** + le protocole qui a attrapé, cette session, **un look-ahead majeur** (trailing-stop Sharpe 2,05 → 0,32 corrigé), confirmé que coût/structure décident, et tenu la ligne « 1 essai ». **C'est le vrai asset CV : la discipline, pas le jackpot.**

---
*Mémo 2026-06-03. Sources : `J1_USDJPY_trend_findings.md`, `TREND_BOOK_progress.md`, `outputs/{usdjpy_clean,gold_clean,book_JG}.parquet`. Cohérent `_FTMO_ETAT_CANONIQUE.md` + `CHARTE_methodo_trendfollowing.md`. Backtest, 0 jour live. 1 seul essai partout.*
