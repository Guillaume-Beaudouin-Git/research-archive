# Entrée de log — session_structural_dislocations (CANDIDAT, à merger par le mainteneur)
*Candidat de section, périmètre session_structural_dislocations uniquement. Numérotation/intégration tranchées au merge. Ne PAS écrire dans le log partagé (collision sessions parallèles). Rien figé.*
*⚠ Re-tread partiel de `session_3` BATCH 2 + `cip_eoq` — à déduper au merge.*

---

## [2026-06] Skew research — session_structural_dislocations (candidats 1-5 : contraintes & dislocations structurelles)

**Objectif** : sleeves skew+ décorrélés pour portefeuille survie-propfirm (L7). Détail : `data/skew_research/session_structural_dislocations/exploration_2026-06.md`.

**Résultat ACTÉ : 0 survivant FTMO-tradeable.** 2 near-miss au bon profil (skew+/décorrélé natifs) mais **différés au sort de l'ORB** — edges intraday sous-puissants en daily, à reprendre SEULEMENT si la mesure de coût intraday (ORB 15h30) revient favorable. Ne pas investir de cycles.

- **#1 reconstitution → flux ETF sectoriel** — ✗ `session_3 B2` (indice net≈0, pas de dates recon, ETF sectoriels non-FTMO). Re-tread.
- **#2 VIX expiry mercredi (SOQ)** — ⚠ near-miss DIFFÉRÉ + **non-FTMO** : spot ^VIX day-after +120bp **t=2,02**, VIXY tradeable +55bp **t=1,76** skew **+1,43**. VIXY/produits vol = **ETF = perso-only (Gate-0 FTMO)**, comme month-end bond. Daily ne capture pas l'auction ; suivi intraday = perso-only seulement.
- **#3 cross-currency basis quarter-end** — ✗ `cip_eoq` KILL (μ net 1-3bps ≪ 24bps, L11 ×5 ; forwards indisponibles gratuits).
- **#4 dividend futures / ex-div** — ✗ data-blocked (pas de dividend futures gratuits ; adjacent `session_3 B4` NAV non-tradeable).
- **#5 leveraged-ETF EOD rebalance** — ⚠ near-miss DIFFÉRÉ : signal propre t=1,15 (cond. gros move SR 0,59, mean monotone en |move| → mécanisme réel), skew_horiz +0,5→+1,1, corrEQ ~0. Edge intraday sous le gate → retombe sur le **tueur n°1 de l'ORB (coût intraday non mesuré)** ; très improbable qu'il survive. **Look-ahead attrapé** (variante t=12,2 fausse : `r_rest⊇r_last30`).

**Candidats-leçons (nommés, à numéroter au merge) :**
- « t spectaculaire = audit artefact obligatoire (3/3) » (look-ahead `r_rest⊇r_last30`, corr=+1,000, t=12,2 faux vs 1,15 ; **3e prise** : trailing-stop, gap-fade, lev-ETF ; vérifier la décompo additive avant tout signal-somme).
- « Near-miss intraday partage le sort de l'ORB » (edge intraday sous le gate daily ne survit quasi jamais au coût intraday — tueur n°1 ORB ; différer au verdict de coût ORB 15h30, ne pas dépenser de cycles).
- « Produits vol / ETF = Gate-0 FTMO (perso-only) » (VIXY non-FTMO-tradeable comme month-end bond ; classer la tradeabilité au pré-flight avant de mesurer un edge).
- « Dislocation structurelle = bon profil (skew+, décorrélé natif), edge intraday/non-FTMO » (#5, #2 : daily caractérise le profil pas la puissance).
- « VIX non-tradeable ≠ VIXY tradeable » (day-after +120bp/t2,02 spot vs +55bp/t1,76 VIXY ; dampening futures+contango ; L23b).
- « Dislocations à data propriétaire = mur récurrent » (3/5 : dates recon, forwards CIP, dividend futures ; pré-flight data obligatoire).

**Statut** : 0 jour live, tout backtest. Réconcilié archive (session_3 B2/B4, cip_eoq — pas de re-preuve). Phase 1 seulement. Coordination : écrit uniquement dans `session_structural_dislocations/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue mainteneur (déduper vs session_3 BATCH 2).
