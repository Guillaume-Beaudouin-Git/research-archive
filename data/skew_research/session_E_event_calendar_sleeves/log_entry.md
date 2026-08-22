# Entrée de log — session_E_event_calendar_sleeves (CANDIDAT, à merger par le mainteneur)
*Candidat de section, périmètre session_E uniquement. Numérotation/intégration tranchées au merge. Ne PAS écrire dans le log partagé. Rien figé. Dédup vs session_B (or-seasonal) au merge.*

---

## [2026-06] Skew research — session_E_event_calendar_sleeves (event-premia & flux mécaniques)

**Objectif** : sleeves skew+/décorrélés TSMOM, FTMO-tradeables, NET-CFD-survivants (L7). Verdict binaire net t>1,5. Détail : `data/skew_research/session_E_event_calendar_sleeves/exploration_2026-06.md`.

**Résultat : 1 famille survivante ÉLARGIE, 0 brique neuve pleinement indépendante.**

- **#2 Saisonnalité précieux-Q1 (Ag/Pt/Pd) — ✅ SURVIT net-CFD** : silver Jan NET +387bp t=3,07, platinum NET +334bp t=3,00 (21 nuits swap métal incluses, robuste à 2× swap), skew+, corr-TSMOM 0,06. **MAIS corr(silver,gold-Jan)=0,86 / platinum=0,42** → élargit le sleeve or de session_B, pas 4 briques décorrélées. Palladium corr 0,09 (indépendant) mais faible (t=1,97, best-month Feb). Silver DSR×12=0,864 FAIL si mois mined / PASS si pré-spec mécanisme. Combiné Ag+Pt : NET +279bp t=2,42 skew+0,35. OOS pre14 +601→post14 +212 (decay net, reste positif).
- **#1 Pré-CB drift ECB/BOE/BOJ/FOMC — ❌ MEURT** net (ECB −28bp full-sample ; FOMC post-2023 +2bp = decay). ⚠ faux-positif attrapé : DTB3 couverture partielle sortait ECB « +38bp t=2,70 » (sous-échantillon).
- **#3 Turn-of-month US500/100/30 — ❌ MEURT** : non distinct du beta long (net t≤1,24).
- **#4 EIA drift WTI — ❌ MEURT** : pas de drift systématique (V-shape non-signif, net Wed −1bp).
- **#5 Reconstitution — ❌ KILL archive** (non-tradeable 23-CFD, effet indice ≈0 ; session_3 B2).

**Candidats-leçons (nommés, à numéroter au merge) :**
- « Saisonnalité précieux-Q1 survit net-CFD ; non-or = surtout beta-or » (silver/platinum net t~3,0 mais corr 0,86/0,42 à gold ; élargit, ne décorrèle pas).
- « Event-premium de résolution ≠ flux mécanique persistant : le 1er décaye et meurt net, le 2e tient » (pré-CB mort vs demande physique Q1).
- « Sample-consistency : RF à couverture partielle fabrique un faux-positif » (DTB3<2026 → ECB +38 t2,70 vs −28 full-sample ; aligner gross/net). 4e faux-positif de l'arc.
- « Net-CFD décide : nuits×swap, pas un RT unique » (~−81bps/mois métal ; seul gross>+400bps survit ; L33).
- « DSR×12 sélection-de-mois : cellule isolée fail (silver 0,864), faisceau-mécanisme valide » (cohérence 4 métaux + keeper gold).

**Action** : verser Ag+Pt(+Pd) au sleeve metals-seasonal de session_B (panier précieux-Q1 plus robuste, skew+0,35), PAS comme briques séparées. Valider sur CFD réel avant live (swap mesuré, pas modélisé).

**Statut** : 0 jour live, tout backtest. HAC lag-6, DSR déflaté, net-CFD swap conservateur. Réconcilié archive (session_B, session_3 B2, session_structural #1 — pas de re-preuve). Coordination : écrit uniquement dans `session_E_event_calendar_sleeves/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue (déduper vs session_B).
