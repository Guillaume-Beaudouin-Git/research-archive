# Entrée de log — session_crossasset_leadlag (CANDIDAT, à merger par le mainteneur)
*Candidat de section, périmètre session_crossasset_leadlag uniquement. Numérotation/intégration tranchées au merge. Ne PAS écrire dans le log partagé (collision sessions parallèles). Rien figé.*

---

## [2026-06] Skew research — session_crossasset_leadlag (candidats 1-5 : cross-asset & lead-lag)

**Objectif** : sleeves skew+ décorrélés pour portefeuille survie-propfirm (L7). Détail : `data/skew_research/session_crossasset_leadlag/exploration_2026-06.md`.

**Résultat : 0 survivant Phase 1.** Aucun sleeve complémentaire. La décorrélation native est présente partout (corrEQ ∈ [−0,36 ; +0,06]) mais creuse — pas d'edge brut derrière.

- **#1 lead-lag cuivre→SP500** — ✗ mort à TOUS horizons (t = −1,54/+0,20/−0,41/−1,04/+0,33 sur 1/3/5/10/20j ; hebdo −0,59). L31 confirmé empiriquement.
- **#2 carry FX G10 hedgé-vol** — ✗ archive (FX-1→FX-4 mort, G1 VXY-vol CLOSED). Cité, non re-mesuré.
- **#3 credit momentum HYG/IEF** — ✗ no edge (t≈0) MAIS forme recherchée (skewM +0,62, corrEQ −0,36). Forme ≠ edge.
- **#4 oil term-structure timé** — ✗ direction carry-correcte *significativement négative* (t=−2,62) → L32 reconfirmé. Inverse signif (t=+2,62, skewM +2,39) mais sign-flip L33 + skew mono-épisode (2020 oil-négatif). Non promu.
- **#5 gold/real-rates** — ✗ faible (t=+0,53), skew horizon −0,43, split-half SR −0,05/+0,31 (régime-instable, piège confirmé).

**Candidats-leçons (nommés, à numéroter au merge) :**
- « Lead-lag publié = arbitré à tout horizon jusqu'à preuve OOS post-publication » (L31 empirique).
- « Carry commodity timé two-sided ne rescape pas L32 » (carry-dir négatif signif ; inverse = sign-flip mono-épisode).
- « Skew+ à l'horizon SANS edge ≠ sleeve » (distinguer forme skew/corr de l'edge t/SR).
- « Décorrélation native ≠ edge » (tout le batch décorrélé equity, 0 alpha — décorrélation = filtre, pas source).
- *(transverse)* « Mesurer le skew à l'horizon de détention » re-confirmé (daily trompe : #3 −0,45→+0,62, #4-inv +0,46→+2,39).

**Statut** : 0 jour live, tout backtest. Réconcilié archive (#2, #4 — pas de re-preuve). Phase 1 seulement. Coordination : écrit uniquement dans `session_crossasset_leadlag/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue mainteneur.
