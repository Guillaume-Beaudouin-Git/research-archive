# Rapport reproductible — Investigation Trend-Following FTMO
### Document de vérification indépendante. Tout est spécifié pour réplication. Script joint : `code/trend_replication.py`.
*2026-06-03. Cohérent avec `_FTMO_ETAT_CANONIQUE.md` + `CHARTE_methodo_trendfollowing.md`.*

---

## 0. Comment vérifier (lecture rapide)
1. Lancer `python code/trend_replication.py` (dépendances : `numpy`, `pandas` ; réseau pour Yahoo).
2. Comparer les chiffres imprimés à la **§5 (Résultats attendus)** ci-dessous.
3. Points de contrôle d'erreur les plus importants : **§4.3 (look-ahead)**, **§3.4 (coût/swap)**, **§3.5 (timing signal)**.
4. Tout écart > quelques % = creuser (données Yahoo peuvent dériver à la marge ; la structure des résultats doit tenir).

> **Verdict (à vérifier, pas à croire) : le meilleur véhicule est le book trend J1+G1 (Sharpe ~0,72) ; sur FTMO 2-step en 1 SEUL essai il plafonne à ~33-36 %. Aucune des 5 familles testées ne passe confortablement. Mur structurel.**

---

## 1. Objectif & cadre
- **But** : maximiser p(pass) d'un challenge FTMO 2-step en **1 SEUL essai** (jamais de % multi-essais).
- **Règles FTMO 2-step** (constantes du sim) : Phase 1 +10 %, Phase 2 +5 %, **DD journalier 5 %** (du solde initial), **DD total 10 % statique** (floor $9 000 sur $10k), min 4 jours/phase, **aucune limite de temps**.
- **Charte** : signal à T-1 / trade à T ; coût mesuré ; full-sample + année-par-année ; bootstrap CI ; pas de tuning (params littérature) ; barrière comme objectif (pas le Sharpe) ; tout backtest, **0 jour live**.

## 2. Données (sources exactes, point-in-time)
| usage | source Yahoo | période | nettoyage |
|---|---|---|---|
| USDJPY (J1) | `JPY=X` | 2000-2026 (6857 j) | glitches : `|ret|>5 %` qui se renverse (somme 2 j < 2,5 %) → interpolation log. 3 corrigés. Pire jour réel **−5,1 %**, vol 9,8 %. |
| Gold (G1) | `GC=F` | 2000-2026 (6460 j) | glitches `|ret|>8 %` round-trip ; 0 trouvé. Pire jour **−11,4 %**, vol 17,8 %. |
| Oil (O1) | `commod_daily['USOIL']` | 2005-2026 | cap returns à ±20 % (avril 2020 prix négatif). vol 41 %, contango 60 %. |
| Crypto (B1) | `BTC-USD` | 2014-2026 (4276 j) | vol 67 %, pire jour −37 %. |
| Carry (proxy) | `^IRX` (T-bill US 13 sem.) − JP≈0 (+0,25/0,5 BoJ 2024+), **laggé 2 j** | — | FRED injoignable depuis le sandbox → proxy ^IRX. **À durcir avec vrais 2y US/JP.** |
| Univers XS/CTA | 31 instruments (FX×9, indices×6, métaux×4, énergie×2, crypto×4, agri×6) | 2000-2026 | cap returns par classe : FX ±7 %, crypto ±40 %, autres ±25 %. |

⚠ **Limite données #1** : Yahoo FX a des ticks aberrants (cf. nettoyage). Le carry est un **proxy** (^IRX), pas le vrai différentiel 2y US-JP (FRED bloqué). À reconstruire avec une source propre avant capital.

## 3. Méthodologie (formules exactes)
**3.1 Signal — TSMOM 12-1 (Moskowitz et al., non tuné)**
`mom[t] = sign( P[t-22] / P[t-252] - 1 )` → ±1. (Momentum 12 mois hors dernier mois ; connu à t-22, donc laggé d'office.)

**3.2 Vol-targeting**
`rv[t] = std(returns, 20j)[t-1] × √252` (vol laggée). `pos[t] = clip(0.10/rv[t], max=3) × mom[t]` (cible 10 % ann, cap levier 3).

**3.3 J1 carry-aligned** : `sig[t] = mom[t] si sign(carry[t])==mom[t] sinon 0`. Comme `carry>0` sur 100 % de la période (US>JP toujours), ce filtre ⇒ **long-only de facto**.

**3.4 Coûts (le paramètre qui décide — L33)**
- Spread RT : FX 0,6 bp · or 1,5 bp · oil 4 bp · crypto 5 bp. Appliqué au **turnover** : `cost = |pos[t]-pos[t-1]| × spread`.
- **Swap/financing** (overnight, multi-jour) : J1 = `+carry/100/252 × pos` (carry encaissé, **tailwind**) ; G1 = `−US_rate×0,9/100/252 × |pos|` (funding payé long, **headwind**) ; CTA/XS CFD = `~1-1,5 bp/jour × exposition brute` (L28 : market-neutral paie 2× le markup).
- ⚠ **Vérif clé** : changer le coût change le signe de l'edge (L33). Le rapport est sur spread serré FX/or ; sur CFD large l'edge dégrade.

**3.5 Timing (anti-look-ahead)** : `strat_ret[t] = pos[t] × ret[t] − coût`, où `pos[t]` n'utilise QUE des données ≤ t-1. **Test de délai** : décaler le signal de +1 j ne doit PAS améliorer (sinon leak).

**3.6 Simulateur de barrière FTMO** (l'objectif réel, pas le Sharpe)
Block-bootstrap (blocs 21 j) des rendements stratégie normalisés unit-vol, × sizing `s`. Chaque chemin : `eq *= (1+s×r)` ; bust si `r×s < −0.05` (daily) **ou** `eq < 0.90` (total) ; P1 si `eq≥1.10` & jours≥4 (reset eq=1, cible 1.05) ; P2 si `eq≥1.05` & jours≥4. p(pass)=fraction financée. nb=9000 chemins, cap 126 j (6 mois), seed fixé.

## 4. Validation & contrôles d'erreur (à reproduire impérativement)
**4.1 Bootstrap CI Sharpe** (block, 2000-3000 tirages) — J1 : SR 0,58, **CI95 [+0,18, +0,96]** (exclut 0 = réel).
**4.2 Stabilité régime** — J1 : 2000-2012 SR +0,53 / 2013-2026 +0,63 (stable). G1 : + sur 3 décennies.
**4.3 DEUX bugs attrapés cette session (à re-vérifier que vous les évitez) :**
- **Look-ahead trailing-stop** : version naïve enregistrait la position APRÈS avoir réalisé le rendement du jour ET déclenché le stop → book Sharpe **2,05** (faux). Corrigé (position de t enregistrée AVANT de voir ret[t]) → **0,32**. Test délai+1 stable = propre. **Si vous obtenez un Sharpe >1,5 sur un trailing-stop, vous avez ce leak.**
- **Blowup numérique CTA** : pondération `mom/vol` explose quand vol→0 → MaxDD −2048 %, skew +24. Corrigé en floorant la vol à 0,3 %/j et cappant les positions à ±3.
**4.4 Annualisation** : stratégies trade ~quotidien (252/an) → √252 OK. *(Candidat nommé « Annualisation √(obs/an) » : un edge hebdo s'annualise en √52 — ne s'applique pas ici. Numéro L non gravé.)*
**4.5 Décomposition beta/alpha (revue équipe, vérifié)** : J1 régressé sur le beta long-USDJPY → **R²=0,51, alpha résiduel +2,1 %/an, t=1,95-1,98**. À reproduire : `np.polyfit(beta_ret, J_ret, 1)` (intercept×252 = alpha, R²=1−var(resid)/var(J)). Verdict = **beta-dominant + alpha résiduel marginal non hedgé** (ni pur beta, ni alpha déployable).

## 5. Résultats attendus (à comparer à la sortie du script)
**5.1 Sleeves (Sharpe net, full-sample)** — *valeurs exactes de sortie du script joint.*
| sleeve | Sharpe | skew | MaxDD | années>0 | verdict |
|---|---:|---:|---:|---:|---|
| J1 USDJPY carry-aligned | **+0,58** | −0,29 | −23 % | — | ✅ réel (CI [0,18;0,96]) |
| G1 Gold TSMOM | **+0,66** | −0,16 | −27 % | 20/26 | ✅ réel (3 décennies) |

> *Note repro : le script donne G1 +0,66 / book +0,70 ; mon analyse inline initiale donnait +0,69 / +0,72 — l'écart (~0,03) vient du choix de modélisation du swap or côté short (le script ne crédite pas le funding aux shorts ; l'inline le créditait). Immatériel au verdict. Si vous obtenez 0,58 / 0,66 / 0,70 / 36 %, c'est conforme.*
| O1 Oil carry+mom | **−0,37** | −0,36 | −51 % | 5/21 | ❌ fail |
| B1 BTC TSMOM | +0,67 | **−0,83** | −34 % | 9/12 | ⚠ skew −, pire jour −9,1 % |
| XS momentum (31) | gross +0,17 / **net −0,49** | — | — | — | ❌ fail (financing) |
| CTA complet (31) | gross +0,34 / **net +0,23** | **+0,70** | −49 % | 15/26 | ❌ dilué < book |

**5.2 Book J1+G1** : corr **+0,02**, **Sharpe +0,70** (script ; inline +0,72), skew −0,36.

**5.3 p(pass) FTMO 2-step — 1 ESSAI (cap 6 mois)**
| config | p(pass) |
|---|---:|
| J1 seul (sizing 1,5 %) | ~33 % |
| **Book J1+G1 (sizing 1,5 %)** | **~36 % full / ~33 % récent** |
| CTA complet | ~22 % |

**5.4 Structure de firme (book J1+G1, 1 essai)** — FTMO 2-step 36 % · 1-step no-daily static 10 % **62 %** · trailing 6 % (futures prop réaliste) 36 % · trailing 5 % 31 %. → *le 62 % exige une firme static-large-no-daily qui n'existe pas (canonique #1) ; les firmes réelles plafonnent ~35 %.*

**5.5 Adaptations** — floor-taper c=0,15 : bust 55 %→27 %, **p(pass) inchangé** (sizing ≠ levier). Crash-filter : inutile (skew inchangé). Trailing-stop : échec (cf. 4.3).

## 6. Caveats & limites connues (honnêteté)
1. **0 jour live** — tout backtest. Paper ≥3 mois avant capital.
2. **Carry = proxy ^IRX** (FRED bloqué) — durcir avec vrais taux.
3. **Swaps modélisés, non mesurés** — mesurer sur démo FTMO (L33, le coût décide).
4. **Données Yahoo** : FX glitchy (nettoyé), oil prix négatif (cappé), histoires différentes (crypto 2014+).
5. **Skew — prior FALSIFIÉ (revue équipe, vérifié)** : "skew négatif structurel / carry-crash" est faux. J1 skew **mensuel +0,70** (quotidien −0,29 = bruit micro-structure) ; 10 pires jours **1/10 en 2008/2020/2022** (pas de cluster crise). À reproduire : `J.resample('ME').sum().skew()` et `J.nsmallest(10).index.year`.
6. **Régime-dépendance** : Sharpe stable mais p(pass) dépend du régime au départ (non chronométrable, bruit blanc).

## 7. Conclusion (falsifiable, 5 familles)
Breakout (mort coût) · Trend single (réel ~0,7) · CTA complet (dilué) · Cross-sectional (fail) · Structure firme (ne sauve pas). **Aucune stratégie price-pattern retail ne passe FTMO confortablement en 1 essai ; plafond structurel ~36 %.** Meilleur actif réel = **book J1+G1**, déployable hors-FTMO (perso/CV). Si vous trouvez une erreur qui casse cette conclusion : réconcilier d'abord (`_FTMO_ETAT_CANONIQUE.md`).

---
*Script : `code/trend_replication.py`. Données : Yahoo (live) + `outputs/commod_daily.parquet`. Seeds fixés. Reproductible.*
