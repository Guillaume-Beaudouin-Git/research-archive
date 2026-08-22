# Réconciliation — `FTMO_Research_Report.docx` ↔ `FTMO_CANONICAL_STATE.md`
*2026-06-03. À lire AVANT le rapport. La source de vérité est `FTMO_CANONICAL_STATE.md`. Le rapport
DOCX reste valable comme exposé de méthode et de processus, mais ses chiffres de p(pass) sont à coût
idéalisé — corrigés ci-dessous. Règle : réconciliation > régénération (le DOCX n'est pas régénéré).*

## Verdict qui prime
**FTMO = CONFIRMÉ-CLOS.** Pas d'alpha retail accessible dans l'arène. Ne pas allouer de cycles.

## Corrections au rapport (le rapport a tort là où il diverge)
1. **Coût (le point décisif — L33).** Le rapport tourne à **~1 bp RT** (et discute 1-2 bps). Le coût
   **réel** est **3 bps** (futures-direct) / **6-10 bps** (FTMO CFD US100 : commission 0 % + spread
   flottant). À ce coût, **mean_R bascule en négatif** → sur une barrière symétrique le drift négatif
   **dérive vers le bust** (pas de « durée pour passer »). ⇒ les p(pass) du rapport sont des **bornes
   hautes à coût idéalisé**, pas le réel. Réel = **NO-GO**.
2. **p(pass).** Le **44 % (régime 2022+)** mis en avant est un **cherry-pick à rejeter**. Le full-history
   ~30 % ≈ le **~33 % canonique** (lui-même à 2 bps idéalisés). p(pass) est **~plat ~33 %** quel que soit
   le sizing ; **~80 % = pure math de container** (no-bust × temps illimité), pas le signal.
3. **Plafond DP.** Correct dans le rapport, à réaffirmer : le sizing DP-optimal est l'**optimum sur toutes
   les politiques** → mieux sizer ne remonte pas le plafond ; le gap à 50 % est une propriété de l'edge.
4. **Spec.** Le rapport décrit la spec **long-only filtrée (« doc3 »)**. La spec **canonique de
   référence** est **ORB V2+E7 two-sided** (Sharpe 0,27, DSR ~0,70, MaxDD −56 à −89 %). **Ne pas
   mélanger** les chiffres des deux specs.
5. **Verdict du rapport.** « Meilleur véhicule ~44 %/30 %, rien ne passe 50 % » → à durcir en
   **CONFIRMÉ-CLOS** : à coût réel l'edge est négatif, donc même le ~30 % idéalisé ne tient pas.

## Item ouvert unique
**Mesurer le spread US100.cash** (canonique §5 : démo, ~5 sessions, log à 15:30 Paris / 16:30 EET ;
seuil de mort ~3 points RT). Tant que non mesuré : **NO-GO par défaut**.

## Ce qu'on garde du rapport (intact)
La méthodologie, le registre « testé et rejeté », les faux-positifs attrapés (leak ML Sharpe 11,
reversal Sharpe 2,0), la preuve du plafond DP, et le book **compte-financé** (#5) — ce dernier reste
le seul terrain à EV positive (hors FTMO).
