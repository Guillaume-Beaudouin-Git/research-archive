# VERDICT — SPX VRP

Date : 2026-05-25
Status : CONDITIONAL GO
Sharpe net retail attendu : 0.4–0.7 (post-2018, post-Volmageddon régime)
Capital minimum requis : $110K+ (marges PM account pour vendre des puts SPX)
Décorrélation portfolio existant : moyenne (VRP corrélé avec strategy A en crise)
Propfirm-fit : non

## Verdict tranché

CONDITIONAL GO uniquement si capital ≥ $110K et compte PM (Portfolio Margin)
disponible. Dans le contexte actuel M1 IEF (capital < $10K), inexploitable.
Le VRP SPX est réel (primes d'assurance structurelles) mais s'est compressé
après Volmageddon février 2018. L'edge n'est pas mort — il est inaccessible
avec le capital disponible aujourd'hui.

## Pourquoi cette conclusion

- **Dew-Becker-Giglio 2025** : sur 1926-2022, l'alpha des options d'indices
  actions est statistiquement indistinguable de zéro une fois le risque de
  variance intégré. Le VRP est une prime de risque, pas de l'alpha pur.
- **Régime post-Volmageddon (fév 2018)** : l'événement a compressé les
  primes structurellement — VIX term structure aplatie, short-vol crowded,
  spike risk repriced. Sharpe retail pré-2018 (≈1.2) vs post-2018 (0.4-0.7)
  selon données empiriques.
- **Capital PM $110K+** : pour vendre 1 put SPX nu (lot minimum) sur compte
  standard margin → $50K requirement. PM réduit à ~$15-20K/contrat mais nécessite
  $110K NAV minimum chez IB. En-dessous de ce seuil, la seule alternative est
  SPY puts (retail, premium réduit) avec Sharpe encore plus faible.
- **Propfirm incompatible** : vente d'options nues interdite sur tous les comptes
  propfirm review (Tradeify, Apex, Topstep).

## Valeur pour CV / Interview

Démontre la maîtrise des options (Greeks, term structure, skew dynamics) et
l'analyse de régime structurel post-Volmageddon. La citation de Dew-Becker-
Giglio 2025 (NBER WP récent) signale une veille académique active, pertinent
pour les interviews buy-side qui sondent la capacité à distinguer prime de risque
versus alpha pur.

## Conditions de réactivation

- Capital personnel ≥ $110K (post-école, premier salaire quant) + ouverture
  compte PM Interactive Brokers.
- Réactivation recommandée avec stratégie de collar (vente puts + achat puts OTM)
  pour borner le tail risk — plus acceptable en gestion patrimoniale.

## Lien vers deep research

[deep_research.md](deep_research.md)
