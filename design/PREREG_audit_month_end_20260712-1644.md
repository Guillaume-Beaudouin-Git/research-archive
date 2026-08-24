# PRÉ-REGISTRATION — Audit adversarial « month-end bounce » (BTC / FTMO)

**Timestamp gel :** 2026-07-12 16:44 Paris · **Auditeur ≠ auteur** · Session fraîche, offline.
**Commit de ce fichier AVANT tout résultat de calcul.** Aucune donnée d'audit calculée à ce stade
(seule la sanity data brute — bornes de dates, fuseau, bar count — a été inspectée : ce ne sont pas
des résultats de l'hypothèse).

## 0. Contrôle d'entrée de session (compte <ACCOUNT_ID> ARMÉ)
Lu en **SSH lecture seule** (aucune interaction terminal MT5), `state.json` VPS 2026-07-12 16:44:04 Paris :
- `kill = 0` · `flat_today = 0` · `positions = []` · fichier `FLAT = ABSENT` → **baseline sûre**.
- Contexte : phase P1, equity 9641.29, vm=14, spec_sha `56fbdde78a2e5c4365…27928` (chaîne gelée).
- Observé sans y toucher (préexistant, hors périmètre) : `targets_status=MISSING` (week-end), `spec_bounds_breach=1`.

## 1. Artefact audité & posture méthodologique
- **Présents :** `Rapport_BTC_intraday_FTMO.docx` (rapport interne) + `SLEEVE_month_end_bounce.md` (fiche).
- **ABSENTS :** le code de repro (`outputs/btc_intraday_ftmo/alpha_vs_beta.py`, `ftmo_barrier.py`) et
  `N_ledger.md`. Vérifié : 0/413 refs git, 6 worktrees, untracked, tout le Desktop.
- **Data brute citée PRÉSENTE :** `data/panels/m5_indices/binance/BTCUSD_M1.csv` (268 Mo,
  2018-01-01→2026-06-01, header `timestamp_utc`, sanity fuseau = **UTC** confirmé : BTC=$13 715 @2018-01-01 00:00).
- **Posture (conséquence du code manquant) :** audit par **recomputation indépendante** depuis la data brute
  citée. C'est plus robuste qu'auditer leur code (on ne lui fait pas confiance). Le compteur d'essais du DSR
  (TEST 1) est reconstruit à partir des specs énumérées dans le **rapport lui-même** (§4, §6 — « 19 specs »).
- Interpréteur gelé : `…/Quant_Trading/Unholy returns/Python3.12.9/myenv/bin/python3` (pandas 3.0.2, statsmodels 0.14.6).

## 2. Chiffres de référence à confirmer AVANT tout (si faux → tout est faux)
Rapport : N=28, net moyen +0,471 %/trade, HAC t=+2,55, brut +0,59 %, MAE moy −0,36 %, MAE pire −3,37 %,
WR 0,75, W/L 1,37. Dérivations attendues :

| Grandeur | Valeur attendue |
|---|---|
| σ net / trade | 0,977 % |
| SR / trade | 0,482 |
| SR annualisé (8/an) | 1,36 (= 0,482×√(8·… voir note)) |
| Coût implicite modèle | 11,9 bps RT |
| Net requis t≥2,5 | 46,2 bps → coût max 12,8 bps |
| Net requis t≥2,0 | 36,9 bps → coût max 22,1 bps |
| **Marge de coût avant t<2,5** | **0,9 bp** |

## 3. Les 5 tests, DANS L'ORDRE, avec KILL RULES gelées VERBATIM

### TEST 1 — DSR du survivant (BLOQUANT)
1. Reconstruire le survivant (last-Fri, `pre<0`, 08:00→11:59 UTC, régime 2023+) → SR_obs/trade, skew γ3, kurt γ4 empiriques sur les ~28 trades.
2. `N_trials` = **19 specs du rapport** (énumérées §5 ci-dessous) **+ DOF internes du survivant** (régime, filtre `pre<0`, fenêtre pré, horizon sortie, jour retenu). Reporter le décompte, justifier chaque incrément.
3. `sd(SR_trials)` sur les 19 SR/trade reconstruits (à défaut de N_ledger : SR≈t/√N par spec depuis les t/N du rapport).
4. `SR0 = sd(SR_trials)·[(1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e))]`, γ=0,5772.
   `DSR = Φ[(SR_obs − SR0)·√(T−1) / √(1 − γ3·SR_obs + (γ4−1)/4·SR_obs²)]`, T=28.
5. Bootstrap CI 95 % sur le net moyen (10 000 resamples).

**KILL RULE (verbatim) :** DSR < 0,80 → sleeve morte, STOP ici, on passe au TEST 4. Entre 0,80 et 0,95 →
zone grise, on continue mais le verdict final ne peut pas être « GO plein ». ≥ 0,95 → on continue.

### TEST 2 — Coût réel FTMO (BLOQUANT)
1. BTCUSD dispo sur le compte Swing <ACCOUNT_ID> ? (market_export.json / doc FTMO / state.json). **Pas de script sur le terminal armé.**
2. Contract size, min lot, step, **levier crypto effectif Swing**, commission/side, spread.
3. Spread réel BTCUSD @08:00 & @11:59 UTC (moments de settlement) — dans la mesure du possible.
4. Modèle de slippage à l'entrée market (`open(08:00)` intouchable).
5. Re-run backtest au coût mesuré → net, t, WR. **Grille de coûts GELÉE :** {11,5 (rapport) · 12,8 (leur seuil t=2,5) · 15 · 20 · 22,1 (t=2,0) · 25} bps RT, + un scénario slippage add-on. Reporter le coût-breakeven pour t=2,5 et t=2,0.

**KILL RULE (verbatim) :** coût total mesuré > 12,8 bps RT → t<2,5 → **STOP**. Coût > 22,1 bps → t<2,0 → mort sans appel.

### TEST 3 — Effet d'expiration ? (HAUTE VALEUR)
Règle **strictement inchangée** (`pre=open(08:00)/open(04:00)−1`, si `pre<0`→long 08:00→close 11:59).
Faire varier UNIQUEMENT la population de jours (**populations GELÉES**) :

| Population | N attendu | Hypothèse |
|---|---|---|
| dernier vendredi du mois | ~28 | +47 bps (référence) |
| tous les vendredis | ~180 | si atténué mais >0 → c'est l'expiry |
| jeudis (contrôle) | ~180 | doit être nul |
| lundis–mercredis (contrôle) | ~540 | doit être nul |

Si les vendredis hebdo montrent un effet → (a) OI notionnel expirant (API publique Deribit) : l'effet scale-t-il
avec l'OI ? (b) les expirations trimestrielles (mars/juin/sept/déc) dominent-elles ? Ces 2 sous-tests sont
gelés ici, exécutés **seulement si** l'étape vendredis-hebdo est positive.

**KILL RULE (verbatim) :** si vendredis hebdo nuls/négatifs ET contrôle jeudi nul → effet confiné au dernier
vendredi, 8/an, **structurellement inintégrable** (0–2 trades/campagne) → **NO-GO définitif**.

### TEST 4 — Portage moteur path-aware sur le book (INDÉPENDANT, PRIORITAIRE — lancé quel que soit 1/2/3)
1. Identifier **quel moteur** a produit le triplet acté (p≈71,4 %, EV +$740, vm14) et le récent (≈70 %/+$678).
   Vérifie-t-il floor daily −5 % + breaker sur **lows M5** ou **closes M5** ? **Surfacer, ne pas deviner.**
2. Si close-only : porter path-aware/MAE, recalculer le triplet à vm14, book complet, post-gate J1.
3. Reporter le **delta** (p(funded), attempts, EV) avant/après + Deflated Sharpe.
Pas de kill rule (diagnostic) ; si delta significatif → vm14 à ré-examiner (décision qui prime sur le sleeve BTC).

### TEST 5 — Intégration book (SEULEMENT si 1 ET 2 ET 3 passent tous ; sinon NON LANCÉ)
1. Book complet (4 sleeves vm14 + BTC), moteur path-aware, modéliser breaker 9650/−3,5 %, `FlattenAll`,
   `g_flat_today`, purge au DayRollover minuit Paris.
2. Balayer levier BTC ∈ {0,25 · 0,5 · 1,0 · 1,5 · 2,0} (jamais 3,33).
3. Triplet marginal par levier : Δp(funded), Δattempts, ΔEV + P(breaker touché par BTC) + coût contamination.

**KILL RULE (verbatim) :** ΔEV/campagne < +$100 OU Δp(bust) > +2 pts → NO-GO.

## 4. Contrainte d'exécution (à acter, §3 du brief) — note d'archi 10 lignes, AUCUN code EA.

## 5. LISTE EXHAUSTIVE DES SPECS (gelée — aucune spec ajoutée en cours de route)
**Univers de trials pour le DSR (les « 19 specs » du rapport, §4/§6) :**
1. F1a ORB breakout 00:00 UTC · 2. F1b ORB breakout 13:30 UTC · 3. F2 US-session long ·
4. F3 pré-event drift FOMC/CPI · 5. TSM intraday inconditionnel · 6. TSM vol-conditionnel ·
7. RSI2 oversold bounce · 8. IBS oversold bounce · 9. VWAP oversold bounce · 10. Options expiry daily ·
11. Options expiry weekly · 12. Options expiry **monthly** (origine du survivant) · 13. Hour-of-day seasonality ·
14. Overnight 21–23 UTC · 15. Turn-of-the-candle (0/15/30/45m) · 16. Cross-asset lead-lag ·
17. Funding-window · 18. Cross-asset pooling monthly-expiry (BTC/ETH/SOL vs DOGE/XRP/BNB) ·
19. Placebo temporel alpha-vs-beta (jours ordinaires vs last-Fri).
**DOF internes du survivant (comptés en sus, TEST 1.2) :** régime {full/2023+/pré-2022}, filtre {pre<0 / seuil / aucun},
fenêtre pré {04:00→08:00 / autres}, horizon sortie {11:59 / autres}, jour {last-Fri / autre rang×jour}.
**Populations testées (TEST 3, gelées) :** last-Fri · tous vendredis · jeudis · lun–mer. Sous-tests conditionnels : OI-scaling Deribit, trimestriel.
**Grille de coûts (TEST 2, gelée) :** {11,5 · 12,8 · 15 · 20 · 22,1 · 25} bps RT + slippage add-on.
**Leviers (TEST 5, gelés) :** {0,25 · 0,5 · 1,0 · 1,5 · 2,0}.

## 6. DÉCLARATION (gelée)
« Si un test kill, on s'arrête, on ne cherche pas de variante de sauvetage. » Toute variante testée après coup
incrémente le compteur d'essais du DSR et sera notée comme telle. Tout triplet cité sous la forme
**(probabilité, attempts moyens, EV)**. DSR reporté explicitement (convention projet). Aucun déploiement,
aucun merge, aucune action sur le compte <ACCOUNT_ID>.
