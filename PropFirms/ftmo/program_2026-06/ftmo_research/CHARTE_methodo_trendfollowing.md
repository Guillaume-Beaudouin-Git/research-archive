# Charte méthodologique — projet Trend-Following propfirm
### Garde-fou institutional-grade. À lire avant toute session TF. Un chiffre qui viole la charte est invalide jusqu'à réconciliation.

---

## Objectif
Maximiser **p(pass)** d'un challenge propfirm (barrières : DD journalier + DD total + cible), **pas** le Sharpe. La barrière, pas le signal, est l'objet.

## Les 7 erreurs interdites (chacune a mordu l'arc ORB) + parade

1. **Coût optimiste → bascule de signe (L33).** Parade : coût **mesuré** (spread démo + slippage + swap overnight réel + roll), stack complet, sensibilité ×2. Gate : gross_edge > 3× coût. *Mesurer le swap EN PREMIER sur l'actif.*
2. **Cherry-pick de régime.** Parade : full-sample **+ année par année**, retenir le chiffre **robuste/pire-cas**, étiqueter IS/OOS/régime.
3. **Look-ahead / leak.** Parade : **signal à T-1, trade à T** ; tout laggé d'1 barre ; macro en **date de publication** ; test délai-+1 (s'il améliore → leak).
4. **Multiple-testing / overfit.** Parade : **pré-enregistrer** params ; params **de la littérature** (12-1 ne se tune pas) ; **DSR** avec vrai compte d'essais ; WF ≥5 folds ; **≤3 mods**.
5. **Stats erronées** (candidat nommé « Annualisation √(obs/an) » — numéro L à trancher au merge). Parade : annualiser par **√(obs/an)** ; **HAC** Newey-West ; **block-bootstrap** (jamais iid) ; Deflated Sharpe.
6. **Mauvais objectif (L35).** Parade : **simulateur de barrière** comme fonction-objectif ; DD-journalier sur **distribution overnight réelle** ; décomposer placebo (container) vs signal ; **DP = plafond**, le sizing n'est pas le levier.
7. **Non-reproductible.** Parade : **un ledger canonique** par stratégie ; seeds fixés ; pipeline modulaire ; **réconcilier, pas régénérer**.

## Pipeline non négociable
`données point-in-time → signal (laggé) → portefeuille (vol-target plafonné par budget DD) → coût (mesuré, stack complet) → simulateur barrière (p(pass), temps, bust) → validation (WF ≥5 + DSR + bootstrap CI + cross-asset)`. Seedé, testé, versionné.

## Spécifique trend-following × propfirm
- **Vol-target plafonné par le budget DD-journalier**, pas seulement par la vol (calme → grosse position → gap → breach).
- **Préserver le skew positif** (queue droite → +10 %) ; ne pas couper les winners.
- **Swap mesuré en premier** (USDJPY long + ; indices/oil long −).
- **Risque jump/intervention borné** (stop/filtre : BoJ, OPEP).
- **Turnover × coût** arbitré (signal lent = moins de coût, plus de lag).

## Checklist pré-vol (avant de croire UN chiffre)
☐ Coût réel mesuré + sensibilité ×2 OK ☐ Signal laggé, délai-+1 ne l'améliore pas ☐ Full-sample + année/année, chiffre robuste retenu ☐ Essais comptés, DSR, ≤3 mods ☐ Objectif = p(pass) barrière, DD sur distribution overnight ☐ Seeds + ledger unique + reproductible ☐ Étiquette IS/OOS/0-jour-live explicite

---
*Charte 2026-06-03. Cohérente avec `_FTMO_ETAT_CANONIQUE.md`. Honnêteté > optimisme. Réconciliation > régénération.*
