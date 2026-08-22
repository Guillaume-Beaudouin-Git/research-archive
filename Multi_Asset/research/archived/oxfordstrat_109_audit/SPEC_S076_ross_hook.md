# Spécification & dossier de vérification indépendante — #76 Ross Hook (premier KEEP)

*But : permettre à une équipe tierce de **ré-implémenter de zéro**, **reproduire les chiffres**, et **challenger** l'edge (erreur ? artefact ? logique tenable ?). `ftmo_lab.py` @ 9dea332. 2026-06-07.*

> ⚠️ **À lire en premier.** Mon moteur teste un **PROXY** de la figure de Joe Ross, pas la détection littérale du 1-2-3. La §3 décrit exactement la différence. Pour un audit honnête, vous devez (a) reproduire mon proxy, **et** (b) décider si le proxy est acceptable ou s'il faut coder le 1-2-3 littéral (question ouverte §10).

---

## 1. Comment utiliser ce dossier
1. Lire §2 (concept) et **§3 (ce que le code fait réellement)**.
2. Ré-implémenter à partir du pseudocode §5 **sans regarder mon code**.
3. Reproduire les chiffres de référence §7 (doivent matcher au chiffre près).
4. Rejouer les tests anti-artefact §8 et la checklist §9.
5. Challenger les limites §10.

---

## 2. Le concept (Joe Ross, littéral)
Le Ross Hook est une **entrée de continuation de tendance**. Séquence classique (côté long) :
1. **Pattern 1-2-3** : en sortie de baisse, point **1** = plus-bas, point **2** = rebond (plus-haut de réaction), point **3** = repli qui s'arrête **au-dessus** du point 1 (plus-bas plus haut).
2. **Cassure** : le prix franchit le point **2** → le 1-2-3 est confirmé (tendance haussière).
3. **Ross Hook** = la **première correction** après cette cassure. Le prix fait un nouveau plus-haut, puis corrige légèrement (le « hook »).
4. **Entrée** : *buy stop* un tick **au-dessus du plus-haut du hook** (reprise de la tendance). Miroir pour le short.

Idée économique : après une rupture de tendance confirmée, la **première respiration** est statistiquement suivie d'une **reprise** → on achète la reprise.

---

## 3. ⚠️ Ce que MON moteur teste exactement (PROXY — divergences explicites)
Je **n'implémente pas** la reconnaissance du 1-2-3. Je remplace « cassure d'un 1-2-3 » par **« nouveau plus-haut sur `Min_Setup` barres »** (proxy de jambe établie), puis « première correction + reprise ». Concrètement (long) :

| Élément Joe Ross (littéral) | Mon proxy (ce que le code fait) |
|---|---|
| Cassure d'un pattern 1-2-3 | `high[i]` est un **nouveau plus-haut sur les `Min_Setup` dernières barres** (`high[i] = max(high[i-Min_Setup+1 … i])` ET `high[i] > high[i-1]`) |
| Plus-haut du hook | **H\*** = ce plus-haut `high[i]` lui-même |
| Première correction | ≥ 1 barre ultérieure avec `high[j] < H*` |
| Buy stop au-dessus du hook | entrée quand `high[j] ≥ H*` (reprise), dans une fenêtre de `Max_Hook` barres |
| Plus-bas du hook (quick stop) | **hooklow** = plus-bas atteint pendant la correction |

**Conséquences à connaître (importantes pour l'audit) :**
- (a) **Plus permissif** que Joe Ross : *tout* nouveau plus-haut N-barres compte, pas seulement ceux qui suivent un 1-2-3 formel.
- (b) Le « hook » de mon proxy = la 1ʳᵉ correction d'un nouveau plus-haut ; il n'y a **pas** de validation de la structure 1-2-3 (points 1/2/3).
- (c) `Min_Setup` chez moi = lookback du plus-haut N-barres (≠ taille du 1-2-3 littéral).
- (d) **Constat empirique (§8.B)** : un contrôle naïf « acheter *chaque* nouveau plus-haut N-barres sans hook » est **déjà positif** (+0,024 R) ; le hook ajoute +0,016 R (~40 %). Donc le fond de l'edge est une **prime de breakout-momentum court terme**, raffinée par le hook. **À garder en tête : ce n'est pas un alpha unique du « hook », c'est du breakout-momentum bien implémenté.**

---

## 4. Paramètres
| Param | Valeur réf. (#76) | Rôle |
|---|---|---|
| `Min_Setup` | 10 barres | lookback du nouveau plus-haut/bas (jambe) |
| `Max_Hook` | 20 barres | fenêtre max entre le plus-haut et la reprise |
| `Time_Index` | 10 jours | sortie temporelle |
| `ATR_Length` | 20 | ATR (True Range moyen) |
| `ATR_Stop` | 6 | stop catastrophe = 6×ATR ; **aussi l'unité de R** |
| `depth_ratio` | None (#76) ; 0,25–2,0 (#78/#79) | filtre profondeur : `H*−hooklow ≤ depth_ratio × (H*−min low jambe)` |
| `RISK_FRAC` | 0,5 %/trade | sizing fixed-fractional |
| coûts | plancher par classe (forex 1,5 / indices 2,0 / commodités 4,0 / crypto 8,0 bps RT) | `round_turn_cost_bps` |

**Univers** : 30 instruments FTMO (10 indices, 9 forex, 9 commodités, 2 crypto). **Déployable recommandé : indices + commodités + crypto (retirer forex, §8.C).**

---

## 5. Pseudocode exact (causal — ré-implémentable tel quel)
```
pour chaque instrument:
  H = high, L = low, O = open, C = close ; A = ATR(20)
  HHk = rolling_max(H, Min_Setup) ; LLk = rolling_min(L, Min_Setup)
  i = Min_Setup + 1
  tant que i < n-1:
    d = 0
    # --- candidat LONG : nouveau plus-haut Min_Setup à la barre i ---
    si H[i] >= HHk[i] et H[i] > H[i-1] et A[i] fini > 0:
        Hstar = H[i] ; legsize = Hstar - LLk[i]
        pulled = Faux ; hooklow = +inf
        pour j de i+1 à min(i+Max_Hook, n-1):
            si H[j] < Hstar:  pulled = Vrai ; hooklow = min(hooklow, L[j])   # correction
            si pulled et H[j] >= Hstar:                                       # reprise
                depth = Hstar - hooklow
                si depth_ratio est None OU depth <= depth_ratio*legsize:
                    d = +1 ; e_detect = i ; e_bar = j
                stop                       # on prend la 1ère reprise uniquement
        # (miroir pour le SHORT : nouveau plus-bas, correction vers le haut, reprise sous L*)
    si d == 0:  i += 1 ; continue
    # --- exécution ---
    # fill réaliste (RETENU pour le verdict) : entry = O[e_bar + 1 + extra_delay]
    # fill optimiste (référence des gates)  : entry = max(O[e_bar], Hstar)  [long]
    risk0 = A[e_detect] * 6
    quick = hooklow (long) / hookhigh (short)      # quick-stop = extrême du hook
    astop = entry - d*risk0                          # stop catastrophe 6 ATR
    pour k de start_j à min(start_j+Time_Index, n-1):
        long : si L[k] <= quick -> sortie quick ; sinon si L[k] <= astop -> sortie astop
        sinon si k == dernier -> sortie au close
    netR = d*(exit - entry)/risk0 - cost_R          # cost_R = coût RT en unités de R
    i = exit_bar + 1                                  # trades NON chevauchants
```

**Points d'implémentation critiques (sources d'écart si mal repris) :**
1. `HHk`/`LLk` **incluent** la barre `i` (fenêtre glissante terminant en `i`).
2. **Aucune** information future : `Hstar` connu en `i`, la reprise se teste avec `H[j]` (barre courante du scan), le fill réaliste est à `O[e_bar+1]`.
3. **R = 6×ATR(barre de détection)**, pas la distance au quick-stop → vos R-multiples seront en unités de 6 ATR.
4. Trades **non chevauchants** (`i = exit+1`).
5. Sortie : quick-stop testé **avant** le stop ATR (le quick est le plus serré pour une correction peu profonde).

---

## 6. Code de référence & données
- Moteur : `code/rosshook.py` (fonction `simulate_rosshook`, ~70 lignes).
- Runner + gates : `code/strat_s076_ross_hook.py`. Deep-dive : `code/s076_deepdive.py`.
- **Données** : `ohlc/*.parquet` (+ `ohlc/_coverage.csv` pour provenance). **Indices = vrai OHLC FTMO** (panel 2000+) ; **commodités = futures continus Yahoo** (proxy, sauf or) ; **or/forex/crypto = M1 rééchantillonné**. Validation données réelles : `code/s076_real_audit.py` n'existe pas encore — la part « données réelles » est dans `s076_deepdive.py` (indices réels + or M1 + crypto).

---

## 7. Chiffres de référence à reproduire (Min_Setup=10, Max_Hook=20, Time=10, univers complet)
| Mesure | Fill optimiste (`stop`) | Fill réaliste (délai+1) |
|---|---|---|
| Trades | 6 939 | 6 577 |
| Win % | 41,6 % | ~41 % |
| expR (net) | +0,0460 | +0,0397 |
| Profit Factor | 1,386 | — |
| Sharpe trade-séquentiel | 1,78 | 1,53 |
| **Sharpe portefeuille mark-to-market** | 1,13 | **0,96** |
| MaxDD réel (MTM) | — | **−6,0 %** |

**Gates (`results/s076_gates.csv`) : 0/4** — délai+1 1,78→1,53 ✅ · two-sided long +0,066/short +0,021 ✅ · DSR 2,63>1,78 ✅ · OOS +0,043→+0,049 ✅.

> Le **MaxDD −79 %** affiché par `trade_metrics` est un **artefact de la métrique séquentielle** (équité compoundée trade-par-trade) — le vrai DD du portefeuille diversifié (mark-to-market) est **−6 %**. À ne pas confondre.

---

## 8. Tests anti-artefact déjà réalisés (à rejouer)
**A. Anti-look-ahead = robustesse au délai d'entrée** (un leak au bar d'entrée s'effondrerait si on retarde) :

| délai | +0 | +1 | +2 | +3 | +5 |
|---|---|---|---|---|---|
| Sharpe trade | 1,78 | 1,53 | 1,49 | 1,58 | 1,68 |

→ stable jusqu'à +5 → **pas de fuite d'information**. (Et : effet **lent**, donc le « hook » précis n'est pas critique.)

**A2. Causalité par troncature (preuve forte anti-look-ahead).** On relance le moteur sur les données **tronquées** à une date T arbitraire (2018-01-01) et on compare aux trades de la série complète. Critère : *tout trade entièrement résolu avant T (`exit < T`) doit être bit-identique*.
- Résultat : **0 trade en désaccord** sur 3 583 trades résolus avant T (entry/dir/netR identiques au 1e-9 près).
- Les seules différences (11 instruments) sont des trades **à cheval sur la coupure** : un hook dont la reprise tomberait *après* T ne peut pas trader sur données tronquées — c'est la causalité qui fonctionne, pas une fuite.
- → **Le moteur est strictement causal** : retirer le futur ne change aucun trade passé.

**B. Placebo** : naïf « acheter chaque nouveau plus-haut 10-barres » (sans hook) expR **+0,0235** ; Ross Hook **+0,0397** → le hook ajoute **+0,0162** (~40 %). Le fond (~60 %) = breakout-momentum générique.

**C. Par classe** (délai+1, IC bootstrap) : indices +0,028 [+0,019;+0,039] ✅ · commodités +0,059 [+0,038;+0,082] ✅ · crypto +0,086 [+0,040;+0,156] ✅ · **forex +0,012 [−0,015;+0,040] (NON significatif → retirer)**.

**D. Données FTMO réelles** (indices vrai OHLC + or M1 2007+ + crypto) : Sharpe MTM **0,70**, **alpha t_NW = +4,0** (β marché < 0). *(C'est le test que #60 échouait avec t=0,6.)*

**E. Facteur tendance** : régression sur **marché + TSMOM 12 mois** → **alpha t_NW = 5,4**, corr(TSMOM)=0,11 → **ni beta marché ni beta tendance**.

**F. Sous-périodes** (Sharpe couvert-beta) : 2000-09 **1,06** · 2010-18 **0,93** · 2019-26 **1,05** → **vivant en récent**.

**G. Coûts** (délai+1) : +0 bps expR 0,040 · +3 0,037 · +6 0,033 · **+10 bps 0,028** → robuste.

**H. Contrôle négatif** : le SMA dual classique (#80) **ÉCHOUE** (DISCARD, beta long) sur le même univers → l'edge n'est pas « la tendance marche ici ».

---

## 9. Checklist de vérification indépendante (pour votre équipe)
- [ ] Ré-implémenter §5 **sans** mon code ; reproduire §7 (trades, expR, Sharpe) au chiffre près.
- [ ] **Audit look-ahead ligne par ligne** : confirmer qu'aucune décision en barre `t` n'utilise `>t` (le fill réaliste = `O[e_bar+1]`).
- [ ] Rejouer la **robustesse au délai** (A) et le **placebo naïf** (B) sur votre implémentation.
- [ ] **Reconstruire la série quotidienne en mark-to-market** (pas de R étalé) et confirmer Sharpe ~0,96 / DD −6 %.
- [ ] **Données réelles** : revalider la part **commodités** sur de l'OHLC broker réel (la mienne est en futures Yahoo proxy).
- [ ] Vérifier la **stabilité hors-échantillon** par walk-forward strict (pas seulement 3 tranches).
- [ ] Contrôler la **capacité** : ~253 trades/an, détention ~11 j, 94 % de jours investis ; corrélation des positions concurrentes en stress.
- [ ] **Slippage des breakouts** : tester en paper-trading (les entrées sont des stops sur cassure).

---

## 10. Limites connues & questions ouvertes (à challenger)
1. **Proxy ≠ 1-2-3 littéral** (§3). *Question ouverte : implémenter le vrai 1-2-3 Joe Ross change-t-il le résultat ?* Hypothèse : marginalement, car l'effet est lent et largement du breakout-momentum.
2. **~60 % de l'edge = breakout-momentum générique** ; le hook raffine ~40 %. Ce n'est pas un alpha « secret », c'est une **prime de breakout court terme bien implémentée**.
3. **Effet lent** (robuste à délai+5) → on pourrait **simplifier** le hook sans perte ; inversement, la précision du hook n'est pas la source de l'edge.
4. **Commodités = données proxy** (Yahoo futures continus) pour la part non-or → **revalidation prioritaire** sur données réelles.
5. **Short faible en MTM** (long-dominé) ; le two-sided passe au niveau trade mais le portefeuille est porté par le long.
6. **R = 6×ATR** (pas la distance au stop) → convention de comparaison inter-stratégies, à reparamétrer si vous sizez sur le risque réel du trade.
7. **1 survivant sur 80 stratégies** (multiple testing) — atténué par : significatif sur 3 sous-périodes disjointes + données réelles + placebo + robustesse coûts/délai, mais à garder en tête.

---

## 11. Reproduction
```bash
cd oxfordstrat_109/code
python strat_s076_ross_hook.py     # gates + grille -> results/s076_gates.csv
python s076_deepdive.py            # look-ahead, placebo, par classe, donnees reelles, couts, figure
```
Vérifier : `git log -1 --format=%h -- code/ftmo_lab.py` == `9dea332` (moteur de base inchangé). Dossier d'audit complémentaire : `AUDIT_DOSSIER_S076.md`.
