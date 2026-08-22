# Deep-dive #60 — Oops Bullish (gap-down-fade, long-only) — **PREMIER KEEP DU PROJET**

**Verdict :** 🟢 **KEEP (watchlist-fort)** — *premier edge en 65 stratégies à survivre à l'audit niveau-S012.* Mean-reversion événementielle, **beta ≈ 0**, alpha significatif et **stable sur tous les régimes (2007→2025)**, drawdown réel **−9,5 %** (pas −66 %). · **Registre :** #60 · Source : Larry Williams, rating C · 2026-06-07.

> 🔔 **On s'arrête et on signale fort**, comme convenu : une mean-reversion qui passe délai+1 **et** bat le beta. Contrairement à S012 (faux positif corrigé), celle-ci **tient** au test décisif : couvrir le beta ne tue pas l'edge.

## Le mécanisme économique (pas juste « ça backteste »)
Gap baissier (`Open[i] < Low[i−1]`) = liquidation/panique à l'ouverture qui **sur-réagit**. Le **reclaim du plus-bas de la veille** (buy stop à `Low[i−1]`) signale que la panique a échoué → rebond de réversion overnight. C'est un effet de **microstructure cross-sectionnel** : on est long de *noms spécifiques au bon moment* (post-gap), pas du marché en continu — d'où le beta quasi nul. Asymétrie confirmée : la jambe **short** (gap-up-fade, #59) **perd** — fader la force dans des marchés qui dérivent à la hausse ne marche pas. Si c'était du simple beta long, le short serait neutre, pas perdant.

## Test décisif — alpha après couverture du beta (la leçon S012)
On convertit la stratégie en **rendements quotidiens de portefeuille** et on régresse sur le buy&hold des classes tradées :

| Mesure | Plein (2000→2025) | 2019+ (rally) |
|---|---|---|
| **beta** au BH tradé | **+0,012 (≈ 0)** | +0,007 |
| **alpha annualisé** | **+3,27 %** | +3,16 % |
| t(alpha) OLS | +15,9 | +9,1 |
| **t(alpha) HAC Newey-West (L=15)** | **+5,41** | — |
| Sharpe brut / **couvert-beta** | 2,96 / **2,87** | — / 2,79 |
| R² (part expliquée par le marché) | **4,4 %** | — |

**Lecture :** couvrir le beta ne change quasiment rien (2,96 → 2,87). C'est **l'inverse de S012**, où la couverture annulait l'edge. Même en corrigeant l'autocorrélation introduite par la méthode (HAC), **t(alpha) = +5,4** (largement > 3).

**Preuve immune à la méthode — bootstrap par blocs du expR par trade :**
- délai 0 : IC95 % **[+0,042 ; +0,072]**, médiane +0,056
- **délai+1 (exécutable) : IC95 % [+0,024 ; +0,054]**, médiane +0,039 → **borne basse > 0**.

L'edge existe **au niveau de l'événement**, sans aucune construction de série quotidienne.

## Où est l'edge / qu'est-ce qui marche moins (par classe, Sharpe couvert-beta)
| Classe | Sharpe couvert | Trades | Lecture |
|---|---|---|---|
| **Commodités** | **+3,35** | 1 301 | le cœur de l'edge (gaps fréquents qui reviennent) |
| **Indices** | **+1,80** | 2 135 | solide |
| Crypto | +0,81 | 64 | faible, peu de trades |
| **Forex** | **−1,56** | 250 | **négatif → à retirer** (le FX ne « gap » quasiment pas) |

→ **Sleeve déployable = indices + commodités (+ crypto), SANS forex** : trades 3 500, Sharpe-trade **+1,66**, Sharpe-portefeuille **+3,14**, alpha **+3,40 %**, t_NW **+5,7**, **MaxDD portefeuille −7,9 %**.

## Robustesse (audit complet)
- **Sous-périodes (Sharpe couvert) :** 2007-2012 **+1,33** · 2013-2018 **+1,19** · 2019-2025 **+1,52**. Stable **y compris la crise 2008** → pas un artefact du rally récent.
- **Drawdown réel :** portefeuille diversifié **−9,5 %** (creux 2023-10). COVID-2020 **−4,0 %**, GFC-2008 **−7,9 %**, 2022 **−7,0 %**. *Le −65,6 % du rapport initial était un artefact de la métrique séquentielle (3 750 trades compoundés un par un) — pas le risque réel.*
- **Fill / coûts :** natif Sh 1,56 → délai+1 **1,10** → close 1,30 ; délai+1 **+2bps** 1,03 / **+5bps** 0,94. Survit au fill réaliste **et** au stress de slippage.
- **Plateau de paramètres :** Sharpe 1,32–1,59 sur toute la grille ATR_Index×Time → pas une cellule chanceuse.

## Réserves honnêtes (anti-sur-crédit S012)
1. **Slippage des jours de gap** = le vrai risque de déploiement : les spreads s'élargissent pile quand on entre (reclaim en vol élevée). Testé à plat jusqu'à +5bps (tient), mais le slippage réel d'un jour de gap peut être 2-3× la normale → **à valider en paper/live**.
2. **Sharpe-portefeuille (2,96–3,14) ≠ Sharpe-trade (1,56–1,66)** : le premier suppose qu'on fait tourner les ~6 positions concurrentes simultanément. Les gaps **se groupent en krach** → les positions concurrentes se corrèlent au pire moment (mais le DD est resté −4 %/−8 % en 2020/2008, donc ça a tenu).
3. **Taille/levier :** telle que sizée (RISK_FRAC 0,5 %/trade) elle est **basse en notionnel** (équity ×3-4 sur 25 ans) ; le DD −8 % autorise du levier pour atteindre la vol cible, mais le levier amplifie le risque slippage.
4. **Sharpe glissant 1 an** plonge sous 0 certaines années (2004, 2012, 2019, 2023) → **edge réel mais volatil**, pas une rente.

## Verdict & recommandation
🟢 **KEEP — promu de BORDERLINE.** C'est le **premier vrai alpha** du projet : beta-neutre, significatif (HAC t=5,4 ; bootstrap délai+1 > 0), **robuste à tous les régimes**, à drawdown maîtrisé (−8/−9 %), avec un **mécanisme économique cohérent** (réversion overnight post-gap, cross-sectionnelle). Les 4 gates n'échouaient que sur two-sided — *par construction* (long-only) ; le 5ᵉ test (beta-apparié) **et** ce deep-dive le **confirment** au lieu de le démasquer.

**Config déployable :** indices + commodités (+ crypto en option), **retirer le forex** ; sortie ATR_Index≈3 / Time≈10 (plateau) ; valider le slippage des jours de gap en paper-trading avant capital réel.

## Repro
`cd oxfordstrat_109/code && python s060_deepdive.py && python s060_deepdive2.py` → `results/s060_deepdive_daily.csv`, `results/s060_deepdive.png`. Dépend de `strat_s058_oops` + `beta_bench`. `ftmo_lab.py` inchangé (9dea332).
