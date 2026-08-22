# Entrée de log — session_E2_seasonal_book (CANDIDAT, à merger par le mainteneur)
*Périmètre session_E2 uniquement. Ne PAS écrire dans le log partagé. Rien figé. Dédup vs session_E/session_B flaggé.*

---

## [2026-06] Skew research — session_E2_seasonal_book (grains/softs + book saisonnier standalone)

**Question** : la mort du moteur (session_F, L36) laisse la structure (B) prime>>carry ; un book saisonnier SEUL clear-t-il +10% phase-1 ? Détail : `data/skew_research/session_E2_seasonal_book/exploration_2026-06.md`.

**(1) Grains/softs : 0 survivant net-CFD.**
- GATE-0 contango : tous PASSENT (drift +3 à +5%/an, pas de bleed UNG-style). Le killer n'est pas le roll.
- NET-CFD : COFFEE-Jul (+181bp gross t1,99 → NET +66 t0,73) et WHEAT-Mai (+241bp t1,69 → NET +126 t0,89) = vrais seasonals tués par swap grain (~−115bp/mois) + **DSR×12 (0,34/0,29)**. SOYBEAN/CORN/COCOA wrong-signed (mois pré-spec = sommets, gross négatif). corr-précieux ≈0 partout.

**(2) Book saisonnier-SEUL (précieux-Q1) = PAS un standalone FTMO viable.**
- Sleeve vol-target 10%/leg EW net swap = **+1,12%/janvier ±2,03%**, tire ~21j/an, worst day −3,48%.
- MC +10% phase-1 (cap −5%/j, breaker −3%, sans limite temps) : L=1 → 99,7% pass mais **8 Januaries (8 ans)** ; L=4 → 1 janvier mais **25,4% breach −5%/jour** ; L=6 → 36% breach.
- **Décompo bust** : le levier requis pour un +10% pratique fait sauter le cap. Cause = sparsité (1 fenêtre/an ne stacke pas). Les grains auraient densifié → mais morts net-CFD.

**Verdict** : précieux-Q1 = topping décorrélé skew+ à poser SUR une structure (A) intraday-flat, **pas** un book autonome. (B) ajoute du rendement décorrélé, ne porte pas la barrière seul.

**Candidats-leçons (nommés) :**
- « Gate-0 contango passe pour les grains ; le killer est swap + DSR×12, pas le roll » (vérifier les deux, pas que le piège session_B).
- « Prime saisonnière survit net-CFD seulement si 2-3× le hurdle » (précieux +468>>81 survit ; grains +180-240 < swap+DSR meurent).
- « Structure (B) trop éparse pour un standalone FTMO » (1 fenêtre/an → +10% = 8 ans ou 25% bust ; topping sur (A), pas book autonome).
- « Vol-target disciplinée ≠ headline spot » (silver-Jan +387bp brut → +1,1%/Jan vol-targeté ; dimensionner à la vol cible avant p(pass)).
- « Mois pré-spec wrong-signed : ne pas re-miner » (soybean/corn juin-juillet = sommets ; rapporter l'échec, DSR×12 0,00).

**Statut** : 0 jour live, backtest. GATE-0 contango, HAC lag-6, DSR×12 déflaté, MC 20k. Réconcilié archive (session_E, session_B, session_F — pas de re-preuve). Écrit uniquement dans `session_E2_seasonal_book/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue.
