# B1 — Month-End Bond Rally ("dash for cash")

> **Statut** : VALIDÉ (phase 2 complète) — sleeve perso, hors FTMO.
> **Meilleur edge mesuré de tout l'exercice skew_research 2026-06.**
> **Source canonique** : `data/skew_research/session_3/exploration_2026-06.md` (BATCH 2 + PHASE 2).
> **Code repro** : `data/skew_research/session_3/code/skew_phase1b.py` + `skew_phase1b_B1holding.py` + `skew_phase2_B1.py`.

---

## Mécanisme

Demande Treasury structurelle « dash for cash » concentrée sur les **3 derniers jours du mois** (rebalancing pension fund / mutual fund / index treasury). L'effet **culmine au month-end** puis se renverse au début du mois suivant → c'est pourquoi la fenêtre TOM (dernier + 3 premiers jours) est nulle alors que les 3 derniers jours seuls sont à t=4,65. Le flux est **bond-spécifique** (TLT/IEF) — pas un proxy via FX/indices (qui ré-introduirait du beta).

Réf. littérature : Etula 2020 (« dash for cash »).

## Spec figée

| Champ | Valeur |
|---|---|
| Direction | LONG Treasury complex (bonds) |
| Fenêtre | 3 derniers jours de bourse du mois calendaire |
| Entrée | close 4-derniers-jours, sortie close month-end |
| Variante délai+1 | entrée +1 jour, hold 2 jours — survit (t=4,45) |
| Univers tradeable | TLT, IEF (ETF) ou ZN, ZB (futures Treasury) |
| Fréquence | ~12 trades/an (1/mois) |
| Vol-targeting | non spécifié — à fixer au déploiement |

## Métriques mesurées (TLT 2002-2026, n=269 mois)

| Version | mean/trade | t | skew (horizon) | hit |
|---|---:|---:|---:|---:|
| **hold 3 j (dend 3,2,1), no-delay** | **+37,5 bps** | **+4,65** | −0,19 | 63 % |
| délai+1 (entrée 1j plus tard, hold 2j) | +30,6 bps | +4,45 | **+0,51** | 61 % |
| dernier jour seul (dend 1) | +17,7 bps | +3,43 | +0,27 | 61 % |

## Robustesses (Phase 2 — toutes barrières passées)

| Barrière | Verdict | Détail |
|---|---|---|
| **Coût (L33)** | ✅ cost-immune | Breakeven swap **~12,5 bps/nuit**. Net +34,5 @1bps, +31,5 @2, +22,5 @5, +13,5 @8 → survit à tout swap réaliste TLT/IEF/futures (où le carry réel ≪ 12,5 bps/nuit). |
| **Régime de taux (Test #3)** | ✅ survit le flip | 2002-2021 bull-bond +39,8 bps t=4,43 ; **2022-2026 bear-bond +28,1 bps t=1,53 brut, +38,9 bps t=2,12 demeaned-within** → **plus fort dans le bear**. Pas un artefact de 20 ans de bull séculaire. |
| **Flow vs beta (Test #4, L25)** | ✅ vrai flux, pas beta | Baseline drift = mean daily ×3 = +4,0 bps. Month-end 3-day = +37,5 → **excès +33,5 bps = 9× le drift**. Demeaned t=4,16. |
| **Consistance temporelle** | ✅ 23/23 années positives | 2004-2026, de +2 à +99 bps/évt. Pas porté par quelques années. |
| **Délai+1 (L26)** | ✅ survit | t=4,45, skew_horizon **+0,51** (devient positif). Pas un artefact de fill / single-print. |
| **Load-bearing** | ✅ dates publiques | Calendrier mois fixe → robuste exécution. |

## Instrument réel — déploiement perso

| Véhicule | Avantage | Inconvénient |
|---|---|---|
| **TLT** (ETF iShares 20+yr) | liquide, accessible compte courtier US standard | dividend swap drag léger, ETF wrapper |
| **IEF** (ETF iShares 7-10yr) | duration moindre, vol plus basse | même remarque ETF |
| **ZN / ZB futures CME** | spread ultra-serré (~0,3 bps RT), pas de carry pur | exige compte futures + marge ~$2-3k/contrat |

→ Recommandation : **ZN futures** si compte futures dispo (coût ≈0,3-1 bps RT, dwarfé par les 37,5 bps/évt). Sinon TLT/IEF (~5 bps RT) reste largement profitable.

## Gate-0 FTMO — POURQUOI HORS-FTMO

> **Test #1 du livrable phase-2 — tradeabilité FTMO : NON.**
> Sources FTMO (FAQ « which instruments », MAJ 2026-05-27) : univers = Forex, Indices, Commodities, Stocks (23 CFD large-cap US), Crypto. Explicitement : **« no access to ETFs, bonds, options, or spot markets »** ; futures non offerts.
> → Aucun instrument Treasury tradeable : pas de bond CFD, pas de ZN/ZB, pas de TLT/IEF (ETF exclus).
> Le flux est bond-spécifique → **pas de proxy FTMO fidèle** (le tenter via FX/indices ré-introduirait du beta).

Conclusion : reclassé **sleeve de portefeuille perso (L7)**, implémentable hors-FTMO. C'est le cas d'école `LESSON-CANDIDATE: venue-instrument-availability-is-gate-0` — stats parfaites mais zéro valeur pour le challenge, grande valeur pour un portefeuille perso.

## Corrélations connues

| Vs | Corr | Source / fenêtre |
|---|---:|---|
| LONG_EQUITY daily (SPY) | **−0,03** | session_3 phase 2 (TLT 3 derniers j vs SPY daily, fenêtre 2002-2026) |
| Strategy A (TSMOM crypto v3) | non mesurée | hors fenêtre commune (B1 monthly, A weekly crypto) |
| Strategy B (delta-neutral HL) | non mesurée | série crypto, non comparable |
| Pré-FOMC (sleeve événementiel) | non mesurée explicitement | profil distinct (FOMC ~7×/an vs B1 12×/an, dates disjointes) |

**Profil portefeuille** : événementiel rare (12/an), série quasi-zéro le reste du temps → corrélations daily mécaniquement ~0 partout (même structure que PREFOMC).

## Réserves / à mesurer au déploiement

1. **Carry réel** sur TLT/IEF/ZN à mesurer broker (breakeven 12,5 bps/nuit → confortable mais à valider).
2. **Vol targeting** à fixer (le sleeve est event-driven, pas continu — sizing par trade plutôt que par jour).
3. **Sizing per trade** à dériver de la vol mensuelle implicite (37,5 bps moyenne, std-dev par trade non rapportée dans le livrable → à calculer si besoin).

## Réconciliation archive

- **Pas dupliqué dans STRATEGY_RESEARCH_LOG.md** (pas encore loggé). Cette fiche est l'unique entrée canonique.
- **Distinct du TOM multi-actifs** (B5) : TOM (dernier + 3 premiers j) est NULL toutes classes (equity, bonds TLT t=−0,17, commo, gold) — il moyenne le rally de fin de mois avec sa réversion de début de mois. Le **« month-end » 3 derniers j ≠ « turn-of-month »**.
- **Distinct du rebalance LS eq-bond** (B1b) : sign(SPY−TLT mois) × spread 3 derniers j → **wrong-signed** (−22,4 bps, t=−1,44, skew −0,78). L'edge vit dans la jambe bond, **pas dans le rebalance equity-vs-bond**.

## Leçons (candidates)

- `month-end-edge-lives-in-the-bond-leg` — l'effet month-end robuste n'est PAS le rebalance-fade equity (wrong-signed) mais la demande obligataire « dash for cash ». Tester la jambe bond, pas la jambe equity-rebalance.
- `turn-of-month-is-fully-arbitraged-but-month-end-bond-is-not` — le TOM (dernier+3 premiers j) est NULL toutes classes ; le month-end-3-day-bond rally survit. Ne pas confondre les deux fenêtres.
- `venue-instrument-availability-is-gate-0` — pour un mandat FTMO, la tradeabilité de l'instrument sur le lieu est un gate-0 à vérifier AVANT le travail statistique. B1 = cas d'école (stats parfaites, instrument exclu).
