# VOLET 1 — Mécanique de suspension J1 (vérifié source primaire, PROPOSÉ non déployé)

**Verdict : FAISABLE, propre, un seul point d'injection, zéro effet de bord destructeur.**
EA/spec gelés INTOUCHÉS. Le brain (extensible) zéroe le poids J1 ; l'EA gelé flatten au 22:05.

## Chaîne (relue ligne à ligne)
```
brain.py (cron 21:50 Paris)
  signals.weights_for(T) → engine.build_signals()  → WT[XAUUSD, USDJPY] (causal shift(1))
  brain.py:107           → weights = {"XAUUSD":…, "USDJPY": wt_row["USDJPY"]}   ◄ INJECTION
  governor.preview()     → engine._target_for_segment → cibles USD = w × scale × eq
  statefiles.build_targets → ea_w_usdjpy (statefiles.py:105) → targets.json
  EA Do2205Rebalance:1067  tgt[1]=JD("ea_w_usdjpy")*sc*eq → TradeLegTo(1, tgt) 
```

## Preuve « w_usdjpy=0 → flatten J1 sans réouverture » (EA gelé, book_executor.mq5)
`Do2205Rebalance` (1067) : `tgt[1]=JD("ea_w_usdjpy")*sc*eq` → `0`. `TradeLegTo(1,0,…)` (555-568) :
- J1 ouvert : `d=0−cur<0` → `reduce=|cur|` → `CloseLegLots(full)` = **flatten intégral**.
- J1 déjà flat : `|d|<LOT_STEP/2` → `return` = **aucune réouverture**.
Miroir exact du sim `_trade_to` (engine.py:182-193). Équivalence EA≡sim verrouillée par la chaîne
de gel. **Le backtest applique la MÊME opération** (`WT[:,1]=0`) → live == backtest par construction.

## Effets de bord (4 sous-questions) — aucun destructeur (source primaire)
| Question | Réponse |
|---|---|
| Renormalisation cross-jambe ? | **NON** — chaque sleeve vol-targetée + clippée indépendamment (engine.py:131,138). |
| Les 3 autres se re-lèvent ? | **Seulement via margin-cap 60 %** (engine.py:373-379). Retirer J1 (51 % du notionnel) **relâche** le cap → sur ~5-6 % de jours où il mordait, gold/US100/GER40 remontent **jusqu'à leur cible propre** (jamais au-delà). Mesuré : `risk_gold 0.323→0.438` sous FULLOFF. Bénin, borné. 95 % des jours : effet nul. |
| book-vol 60d / equity-gate MA100 ? | **NON affectés** — OR-only, sur la courbe d'equity SIMULÉE de la sleeve OR (DOC_SIGNAL_PIPELINE §1-2). |
| scale re-calé ? | **NON** — `scale=vm·taper·glide·pace` ne dépend que de l'equity compte + temps (engine.py:346-354). |

## Divergence sim assumée (documentée, pas un bug)
Suspendre J1 fait diverger le live du sim audité (qui inclut J1). Décision de risk-management,
bornée à la zone, tracée dans `audit["j1_gate"]` de targets.json. Coût mesuré (Volet 2) : gate
opérationnel ≈ 0 (Δp +0.65 [0, +1.95] pts) ; borne pire-cas (suspension permanente) −7.58 pts.

## Patch PROPOSÉ (AVANT / APRÈS) — **non appliqué, pour GO**
Seuils dans un config HORS chaîne gelée (`ftmo_live/config/j1_gate.json`), logique = `gate.py`
(ce dossier, identique au backtest). Aucune ligne de l'EA ni du yaml gelé.

**`ftmo_live/config/j1_gate.json`** (nouveau) :
```json
{ "enabled": true, "t_off": 160.0, "t_on": 155.0, "n_resume": 10 }
```

**`ftmo_live/brain.py`** — insertion après la l.107 (`weights = {...}`) :
```python
# AVANT
    weights = {"XAUUSD": float(wt_row["XAUUSD"]), "USDJPY": float(wt_row["USDJPY"])}
    audit["signals"] = sig_diag
    audit["weights"] = weights
# APRÈS  (+ import: from lib import j1_gate  ;  gate lit panel_px USDJPY du cache, causal ≤ T-1)
    weights = {"XAUUSD": float(wt_row["XAUUSD"]), "USDJPY": float(wt_row["USDJPY"])}
    gate = j1_gate.evaluate(cache)                 # {suspend, level, t_off, t_on, n}
    if gate["suspend"]:
        weights["USDJPY"] = 0.0                    # → ea_w_usdjpy=0 → EA flatten J1 @22:05
    audit["signals"] = sig_diag
    audit["j1_gate"] = gate                        # traçabilité complète dans targets.json
    audit["weights"] = weights
```

**`ftmo_live/lib/j1_gate.py`** (nouveau, ~15 lignes) — réutilise la logique `gate.py` :
```python
def evaluate(cache):
    cfg = json.loads((CONFIG_DIR / "j1_gate.json").read_text())
    px = pd.read_parquet(Path(cache) / "panel_px.parquet")["USDJPY"].dropna()
    off = _off_state(px, cfg["t_off"], cfg["t_on"], cfg["n_resume"])  # = gate.off_state
    # le cache live finit à la dernière close <= T-1 → off.iloc[-1] = décision causale du jour T
    return dict(suspend=bool(cfg.get("enabled", True) and off.iloc[-1]),
                level=float(px.iloc[-1]), **cfg)
```
Causalité : le cache live finit à close[T-1] → `off.iloc[-1]` = OFF-state[T-1] = MÊME sémantique
que le backtest (`suspend_causal` = `off_state.shift(1)`). Test : `brain.py --dry-run --as-of` doit
échoer le `suspend` sur une date en zone.

## Kill-switch existant ≠ suspension J1
`FLAT` (kill-file) = flatten **tout le book** + désarme (mq5:1475-1484) — PAS de suspension
par-sleeve. Le gate brain est le seul moyen propre de flat J1 seul sans toucher l'EA gelé.

## Ce qu'il reste à faire avant déploiement (GO requis)
1. Ratifier les seuils (T_off/T_on/N — défaut 160/155/10, ou 158/155/10, cf. AskUserQuestion).
2. Créer `config/j1_gate.json` + `lib/j1_gate.py` + le patch brain.py (3 lignes) dans un worktree,
   pytest `test_brain_dryrun` + un test gate dédié, présenter le diff.
3. Déployer via pull VPS (brain.py seul ; EA/yaml/mqh INCHANGÉS → pas de recompile).
4. Vérifier en dry-run puis premier soir armé : `audit.j1_gate` présent, `ea_w_usdjpy=0` quand en zone.
```
