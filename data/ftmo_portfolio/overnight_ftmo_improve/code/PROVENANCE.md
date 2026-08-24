# Provenance des modules réutilisés

`overnight_series.py`, `basket_series.py`, `basket_inject.py`, `basket_fp.py` sont extraits
**VERBATIM** de la branche `claude/overnight-basket-ftmo`
(`data/ftmo_portfolio/overnight_basket_feasibility/code/`), elle-même validée
(sleeve-OFF → pooled challenge 0.87, |Δ|=0 vs canonical). Réutilisés read-only ; ils importent
le moteur v2.2 audité + caches depuis le main dir par chemin absolu (gitignored/locaux).
Le code spécifique à cette étude (pistes 0-3) est dans `piste_*.py` / `q_*.py`.
