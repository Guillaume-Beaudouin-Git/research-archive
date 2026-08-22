# PIPELINE v2 — Gates constitutionnels obligatoires

**Date :** 2026-06-04 · **Déclencheur :** audit `AUDIT_S001_crabel.md` (KEEP → DISCARD, 5/6 gates FAIL).
**Portée :** s'applique à **toutes** les stratégies à partir de S001 (rétroactif) et S002…S109.

---

## 1. Pourquoi ce changement

La barre v1 — « **tout edge positif après coûts** » — est **nécessaire mais pas suffisante**.
L'audit de S001 l'a démontré : un edge poolé positif (+0,0068 R, PF 1,05, Sharpe 0,22), robuste
sur 100 % d'une grille de 42 cellules, qui passait la barre v1 en *KEEP borderline*, était en
réalité un **mirage** :

1. **Artefact de fill intrabar** — l'edge n'existait que parce que l'entrée était supposée se
   faire *au niveau exact du stop* sur la barre de breakout. Avec un fill réaliste (open du
   lendemain ou close du jour), le Sharpe passait de **+0,22 à −0,72** (signe inversé).
2. **Beta long déguisé** — 342 % du PnL net venait des **longs** (Sharpe 1,05) ; les shorts
   perdaient (Sharpe −0,18). Ce n'est pas un breakout symétrique mais un filtre de long-trend
   sur des indices qui ont monté.
3. **Bruit de multiple testing** — le « best cell » mis en avant était très en-dessous de
   l'espérance du maximum de 42 tirages de bruit (DSR z négatif).
4. **Mort hors échantillon** — edge entièrement porté par 2000-2015 ; flip de signe sur
   2016-2026.

Aucun de ces défauts n'était visible sous la barre v1. **C'est un défaut de pipeline**, pas une
erreur de mesure (les chiffres bruts de S001 sont reproductibles à l'identique). La correction
consiste à **durcir le moteur en amont** pour que `KEEP` ne soit jamais prononcé sur un mirage.

---

## 2. Ce qui change dans `ftmo_lab.py` (v1 → v2-gates)

### 2.1 Simulateur
- `simulate_bracket(..., fill=...)` accepte désormais un **mode de fill** :
  - `'stop'` (défaut) : fill au niveau du stop intrabar — **optimiste**, reproduit les chiffres v1.
  - `'close'` : fill au close de la barre de breakout — **réaliste** (même barre).
  - `'next_open'` : fill à l'open de la barre suivante — **réaliste, délai+1**.
- Chaque trade porte maintenant `dir` (+1 long / −1 short / 0 = double-touche perdante),
  requis par le gate two-sided.
- **Le chemin par défaut (`fill='stop'`) est inchangé** → la reproduction des mesures v1 (S001)
  n'est pas cassée. Seul le **verdict** change, via les gates.

### 2.2 Quatre gates réutilisables (strategy-agnostic)
| Fonction | Loi | Rôle |
|---|---|---|
| `gate_delay1(run)` | L26 | re-price l'edge en fill réaliste ; FAIL si effondrement/inversion |
| `gate_twosided(trades)` | L25 | split longs/shorts ; FAIL si un côté >70 % du PnL+ et l'autre ≤0 |
| `gate_dsr(grid_sharpes, sr_obs, pooled_netR)` | DSR | Deflated Sharpe sur N cellules ; FAIL si `SR_obs < E[max bruit]` |
| `gate_oos(trades, split)` | L31 | split ≤2015/≥2016 ; FAIL si flip de signe / test ≤0 |

`run_gates(run, sharpe_grid, split)` orchestre les 4 et renvoie le verdict structuré.

### 2.3 Contrat d'intégration pour une stratégie
La stratégie fournit :
- une fonction `run(fill=...) -> DataFrame de trades poolés` (paramètres figés au point de réf.) ;
- `sharpe_grid` = Sharpe par cellule de son balayage (N essais, pour le DSR).

```python
res = ftmo_lab.run_gates(make_run(params), sharpe_grid, split='2015-12-31')
# res['verdict'] ∈ {KEEP, BORDERLINE, DISCARD} ; res['gates'] = détail par gate
```

---

## 3. Nouvelle règle de verdict (stricte)

```
edge_net > 0 (après coûts)         [nécessaire, barre v1]
  ET Gate 1 délai+1   PASS
  ET Gate 2 two-sided PASS
  ET Gate 3 DSR       PASS
  ET Gate 4 OOS       PASS
--------------------------------------------------
=> KEEP        (BORDERLINE si 4/4 mais Sharpe < 0,5)
sinon          => DISCARD (avec tags)
```

Les gates sont dans le **test principal** de chaque stratégie (section 8 du rapport), **pas**
dans une checklist d'audit a posteriori. Le rapport ne peut pas afficher KEEP sans la table des
4 gates.

---

## 4. Validation rétroactive sur S001 (cohérence avec l'audit)

Mesures de base **inchangées** (3 841 trades, +0,0068 R, PF 1,05, Sharpe 0,22, best cell
6R/40j +0,0387, grille 100 % positive). Sous v2-gates :

| Gate | Pipeline v2 | Audit | Cohérence |
|---|---|---|---|
| 1 — Délai+1 | Sharpe +0,22 → **−0,74**, expR −0,0223 | −0,72 / −0,0234 | ✓ (next_open vs i+2) |
| 2 — Two-sided | long +0,0528 (n=1689) / short −0,0096 (n=1588), contrib **342 %** | 341,6 % | ✓ exact |
| 3 — DSR (N=42) | SR_obs **1,247** < E[max] 2,157, z **−37,5** | z −122,9 | ✓ même verdict* |
| 4 — OOS | train +0,0206 (Sh +0,58) → test **−0,0056** (Sh −0,21) | idem | ✓ exact |

\* **Écart méthodologique DSR assumé :** notre gate déflate le Sharpe de la **cellule
sélectionnée** (best = 1,247), quantité correcte pour le Deflated Sharpe. L'audit déflatait le
Sharpe poolé représentatif (0,216), d'où z = −122,9. Les deux sont **très en-dessous** de
E[max] = 2,157 ⇒ FAIL dans les deux cas. La formule E[max] = √(2·ln N)·(1 − γ/√(2·ln N)) est
identique. (Caveat connu : essais non indépendants ⇒ DSR conservateur ; ne sauve pas le verdict.)

**Résultat : VERDICT FINAL = DISCARD (4/4 gates FAIL).** Conforme à l'audit (qui ajoutait
cost-stress = PASS et bootstrap = FAIL ; voir §5).

---

## 5. Gates non inclus dans le bloc obligatoire (recommandés en §9 du rapport)

L'audit utilisait 6 gates. Les **4 décisifs** (délai+1, two-sided, DSR, OOS) sont désormais
**obligatoires dans le moteur**. Deux autres restent recommandés en complément (non bloquants,
faciles à ajouter par stratégie) :
- **Cost-stress ×1,5 / ×2 (L33)** — robustesse aux coûts (S001 : PASS).
- **Block-bootstrap 95 % CI** — significativité de l'expectancy (S001 : IC traverse zéro = FAIL).

Ils pourront être promus en gates obligatoires si le besoin s'en fait sentir sur S002+.

---

## 6. Impact sur le workflow S002…S109

1. `build_ohlc_store.py` et `ftmo_lab.py` sont **partagés et figés** (v2-gates).
2. Par stratégie : un `strat_sNNN_*.py` (signaux + `run(fill=...)` + balayage + `run_gates`) et
   un `REPORT_SNNN_*.md` suivant `TEMPLATE_report.md`.
3. Le rapport **doit** contenir la table des 4 gates (§8) et un verdict conforme à la règle §3.
4. `KEEP`/`BORDERLINE` ⇒ candidat pour approfondissement/optimisation/combinaisons.
   `DISCARD` ⇒ archivé avec ses tags (artefact de fill / beta déguisé / bruit / décayé).

*Fin de la note. Le pipeline v2-gates est prêt pour S002+.*
