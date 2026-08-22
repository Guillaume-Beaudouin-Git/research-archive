# Entrée de log — session_vol_tail (à merger dans STRATEGY_RESEARCH_LOG.md)
*Candidat de section, périmètre session_vol_tail uniquement. Numérotation/intégration tranchées au merge par le mainteneur. Ne PAS écrire dans le log partagé (collision sessions parallèles).*

---

## [2026-06] Skew research — session_vol_tail (candidats 1-5 : vol, structure & queue)

**Objectif** : sleeves skew+ décorrélés pour portefeuille survie-propfirm (L7). Détail complet : `data/skew_research/session_vol_tail/exploration_2026-06.md`.

**Résultats (5 candidats, 3 phases) :**
- **#5 Reversal 1j court-terme (SPX)** — ✅ **SEUL sleeve complémentaire candidat.** skew **+0,71**, décorrélé (corr ~0 aux sleeves, +0,15 beta equity), SR net 0,21-0,43. Edge connu/décayé à l'archive (short-term reversal, L31) — **angle neuf = profil skew+**. ⚠ **non-déployable tant que non levé** : délai+1 s'effondre (0,57→0,08) → valider capturable open→close (risque close-print).
- **#1 VIX-term carry timé** — écarté pour CET objectif. Vrai edge robuste (SR 0,69, cost/OOS-stable) mais skew neutre (−0,02) + beta equity (+0,26) + redondant trend (+0,37). Archive "VIX term Sharpe 0,67 insufficient" — angle neuf : le timing term-structure neutralise le skew du short-vol nu (−1,66→−0,01).
- **#2 VRP** — écarté. skew −1,70 natif (piège short-vol confirmé). Archive (SPX VRP wrong-dir, BTC VRP L13).
- **#4 Bond momentum (Baltussen)** — version intraday data-blocked ; proxy daily TLT sans edge. → renvoi à l'actif `zn_baltussen`.
- **#3 Dispersion** — data-blocked (IV options composants+indice non dispo gratuit).

**Candidats-leçons (nommés, à numéroter au merge) :**
- « Timing term-structure neutralise le skew du short-vol » (VIX nu −1,66 → timé −0,01, edge intact).
- « Skew = dimension de sélection distincte du Sharpe » (caractériser le profil de skew même sur edges archivés jugés sur Sharpe/IC).
- « Reversal court-terme : skew+ mais load-bearing = exécution au close » (délai+1 le tue → drapeau exécution).

**Statut** : 0 jour live, tout backtest. Réconcilié archive (pas de re-preuve). Coordination : écrit uniquement dans `session_vol_tail/`, non touché aux autres sessions ni `overnight_research/`.
