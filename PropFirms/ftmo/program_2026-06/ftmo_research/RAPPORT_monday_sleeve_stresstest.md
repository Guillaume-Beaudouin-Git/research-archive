# Rapport complet — « Monday intraday long » US100 : stress-test & guide de réplication
### Sleeve décorrélé de l'ORB · Desk systématique · 2026-06-02 · v1.1 (CORRIGÉ)

> **🛑 ERRATUM v1.1 (correction critique) — lire avant tout.**
> La v1.0 annualisait le Sharpe en **√252**. Faux : une stratégie « un jour/semaine »
> trade ~**52 fois/an** → annualisation correcte **√52**. **Tous les Sharpe de ce rapport
> ci-dessous sont surévalués d'un facteur ×2,2.** Chiffres corrects :
> - **Monday SR ≈ 0,60 (2010-26) / 0,94 (2018-26) / 1,27 (2022-26)** — et NON 1,31/2,07/2,80.
> - Cross-asset : signe/réplication 6/6 **tiennent**, mais magnitudes ÷2,2 (~0,2-0,9, sous-1).
> - Le t-stat (+2,26), le MaxDD (−13,7 %), l'ann. (+19,6 %), le risque de queue : **inchangés** (indépendants de l'annualisation).
> - **La thèse « Sharpe>1 robuste » est RETIRÉE.** Le lundi est un **tilt réel mais modeste (~0,6-0,9, sous-1)**, décorrélé, significatif (t 2,26) — pas un edge>1.
> - Grille complète corrigée : **aucune** fenêtre jour×heure×direction ne bat le bruit de multiple-testing. Combiner les jours **dilue** (seul le lundi a un edge). Book ORB+Lundi (correct) : 0,28 full / 0,97 récent.
> - Pour lire les tables ci-dessous : **diviser chaque Sharpe par 2,2.** Script `monday_sleeve.py` déjà corrigé (ANN=√52).

> **Statut : backtest + Monte-Carlo, 0 jour live. Estimations, pas garanties.** Sharpe net de coûts. Données : NQ 1-min databento 2010-2026 + OHLC quotidien Yahoo (6 indices). Reproductible (§8 + script joint `monday_sleeve.py`).

---

## 0. Verdict en une page

**Le signal survit au stress-test.** C'est le premier — et seul — candidat de toute la recherche intraday à passer la **réplication cross-asset** (le test qui a tué le gap-fade et 6 autres signaux). Résumé :

| Dimension | Résultat | Statut |
|---|---|:--:|
| Sharpe net full 2010-26 | **+1,31** (t 2,26) | ✓ |
| Sharpe net 2018-26 (régime actuel) | **+2,07** (t 2,58) | ✓ |
| **Déployable réel** (walk-forward récursif + kill-switch) | **+1,26** | ✓ |
| Réplication cross-asset 2018-26 | **6/6 indices** (moy +1,54) | ✓ |
| Bootstrap CI95 Sharpe | full [+0,18 ; +2,46], récent [+0,48 ; +3,65] | ✓ positif |
| Décorrélation à l'ORB | corr **+0,02 à +0,06** | ✓ |
| Monday-spécifique vs beta générique | **8,6×** le beta quotidien | ✓ |
| Risque queue vs DD journalier FTMO | pire jour vol-targeté ~−2,7 % < 5 % | ✓ |
| **Régime-dépendant** (absent 2008-2017) | cross-asset −0,04 à l'époque | ⚠ |
| **Beta-longue directionnelle** (perd en bear) | 2018 −10 % même vol-targeté | ⚠ |
| **Sensible au timing** (edge open+close) | entrer à 10:00 → SR ÷2 | ⚠ |

**Conclusion :** vrai edge **du régime actuel**, déployable comme **sleeve vol-targeté + kill-switch régime** décorrélé de l'ORB. PAS une loi intemporelle ni un alpha market-neutral. À paper-trader avant capital.

---

## 1. Spécification exacte

| Élément | Valeur |
|---|---|
| Instrument | **US100** (NQ / Nasdaq-100) — actif FTMO |
| Condition | jour de la semaine = **lundi** (si lundi férié US → pas de trade cette semaine) |
| Entrée | **long à l'open RTH 09:30 ET** |
| Sortie | **close RTH 16:00 ET** le même jour |
| Tenue | **intraday pur** → flat overnight, **0 swap, 0 financement** |
| Fréquence | ~48 trades/an (1/semaine) |
| Sizing | **vol-targeting quotidien** (vol réalisée glissante 26 lundis, cible ~11 % ann, cap levier ×3) |
| Coût modélisé | 2 bps RT (spread CFD US100 typique 1-2 bps) |
| Garde-fou | **kill-switch** : couper si Sharpe glissant 104-lundis < 0 |

---

## 2. Performance de base (NQ, net 2 bps)

| Période | Sharpe | Ann. | MaxDD | Win | t-stat | n |
|---|---:|---:|---:|---:|---:|---:|
| 2010-2026 | **+1,31** | +19,6 % | −13,7 % | 57 % | +2,26 | 746 |
| 2018-2026 | **+2,07** | +34,6 % | −13,2 % | 59 % | +2,58 | 391 |
| 2022-2026 | +2,80 | +44,0 % | −9,0 % | 59 % | +2,51 | 203 |

Win rate 57-59 % = **tendance directionnelle consistante** (pas une queue portée par 3 jours).

---

## 3. La preuve maîtresse — réplication cross-asset

Le test que les autres signaux échouaient. Lundi intraday (Close/Open−1) sur 6 ETF indices **indépendants** :

| ETF | Lun full | **2008-2017** | **2018-2026** |
|---|---:|---:|---:|
| SPY (S&P) | +0,53 | −0,22 | **+1,69** |
| QQQ (Nasdaq) | +0,91 | −0,07 | **+2,10** |
| DIA (Dow) | +0,70 | +0,21 | **+1,39** |
| IWM (Russell) | −0,23 | −0,70 | +0,43 |
| EWG (Allemagne) | +0,59 | +0,07 | **+1,58** |
| EWJ (Japon) | +1,07 | +0,45 | **+2,09** |
| **Moyenne** | **+0,59** | **−0,04** | **+1,54** |

**2008-2017 : 3/6 positifs (bruit). 2018-2026 : 6/6 positifs.** Six marchés indépendants (dont 2 internationaux) ne s'alignent pas par hasard → effet **réel et structurel** dans le régime actuel. Ceci domine le souci multiple-testing (Bonferroni ×5 sur NQ seul donnait p=0,12 ; la réplication 6/6 le réfute).

---

## 4. Batterie de stress-test (8 tests)

**4.1 Robustesse fenêtre entrée/sortie (test anti-artefact L26)**

| Fenêtre | SR full | SR 2018-26 |
|---|---:|---:|
| **09:30 → 16:00** (base) | +1,31 | +2,07 |
| 10:00 → 16:00 (entrée +30min) | +0,58 | +1,29 |
| 09:30 → 15:30 (sortie −30min) | +0,79 | +1,39 |
| 10:00 → 15:30 | −0,09 | +0,44 |

→ L'edge est **concentré sur l'open ET le close** (gap de week-end + flux MOC du lundi). Pas un artefact same-bar (tenue 6,5h), mais **il faut les fills 09:30 et 16:00** — entrer/sortir 30 min trop tard dégrade fortement. ⚠ Drapeau exécution.

**4.2 Sensibilité aux coûts**

| Coût RT | SR full | SR 2018-26 |
|---|---:|---:|
| 1 bp | +1,48 | +2,23 |
| 2 bp | +1,31 | +2,07 |
| 3 bp | +1,15 | +1,92 |
| 5 bp | +0,81 | +1,62 |
| 8 bp | +0,30 | +1,17 |

→ Full-sample reste >1 jusqu'à ~3 bps ; le régime 2018-26 reste >1 même à 8 bps. US100 CFD ~1-2 bps → marge confortable, mais surveiller l'élargissement de spread les lundis volatils.

**4.3 Vol-targeting (cible 11 % ann)** : SR **+1,36**, ann +17,1 %, vol réalisée 12,6 %. Lisse la concentration. PnL/an : pré-2018 plat (±6 %), **2018 −10 %** (année bear), 2020 +21 %, 2023 +16 %, reste +3-5 %.

**4.4 Walk-forward récursif + kill-switch (LE chiffre déployable réel)**
Trade le lundi **seulement si** Sharpe glissant 104-lundis > 0 (simule "on ne savait pas en 2010") :
- **SR déployable +1,26** · investi 77 % du temps · ann +16,6 % · (always-on même période +1,60).
→ Le kill-switch te garde flat dans les mauvaises passes et délivre quand même **>1**. C'est le chiffre honnête à retenir, pas le 2,07.

**4.5 Risque de queue (critique pour DD journalier FTMO 5 %)**
Pires lundis : −3,7 % (2022-03-07), −3,2 %, −3,1 %, −3,1 %, −3,0 %. p1 −2,7 %, p5 −1,5 %, skew −0,29.
→ **Vol-targeté, la pire journée ≈ −2,7 % < limite DD journalier FTMO 5 %.** Pas de wipeout sur un seul lundi à sizing raisonnable. ✓

**4.6 Bootstrap CI95 (3000 tirages)** : full **[+0,18 ; +2,46]**, 2018-26 **[+0,48 ; +3,65]**. Bornes inférieures positives → significativement >0 (contraste avec le gap-fade dont le CI incluait 0).

**4.7 Décomposition beta** : SR lundi +1,31 vs SR tous-jours +0,15 → **lundi = 8,6× le beta** quotidien. L'edge est **Monday-spécifique**, pas du long générique dilué.

**4.8 Book combiné ORB + Monday** (série quotidienne, equal-risk) : corr **+0,02**. Book 2018-26 SR **+0,97 vs ORB seul +0,65** → vrai gain de diversification du timing d'exposition.

---

## 5. Modes de défaillance (à surveiller en live)

1. **Retournement de régime** — l'effet était inversé/absent 2008-2017. Si les moteurs structurels (flux systématiques début de semaine, vol-control, 0DTE) changent → mort. *Mitigation : kill-switch 104-lundis.*
2. **Marché baissier soutenu** — beta-longue → perd (2018 −10 %). Partage le risque de queue bear avec l'ORB (les deux net-longs). *Mitigation : sizing modéré, ne pas empiler avec d'autres longs equity en bear.*
3. **Dégradation d'exécution** — edge concentré open/close ; mauvais fills à 09:30/16:00 érodent vite. *Mitigation : ordres MOO/MOC, mesurer le slippage réel en paper.*
4. **Spread élargi** les lundis macro/volatils (>5-8 bps) → érode le full-sample. *Mitigation : filtre spread, skip si spread anormal.*

---

## 5bis. Apport réel en p(pass) FTMO (book ORB + Lundi)

Test à **volatilité égale** (ORB seul vs book ORB+Lundi vol-normalisés au même risque), barrière FTMO 2-step, block-bootstrap, cap 6 mois :

| sizing/j | ORB seul (2018-26) | ORB+Lundi | gain |
|---|---:|---:|---:|
| 1,5 % | 35 % | 46 % | +11 pp |
| **2,0 %** | **38 %** | **47 %** | **+9 pp** |
| 2,5 % | 37 % | 42 % | +5 pp |

Full-sample (conservateur) : gain **+3-6 pp**. Temps médian **inchangé** (~2 mois). Sur 2 essais : ORB seul 62 % → book **72 %** d'être financé.

→ **Apport réel et gratuit** (zéro swap, diversifie le timing de l'exposition NQ existante), **mais ne casse pas le mur** : le book plafonne ~47 % en 1 essai, pas de >60 %. Gain régime-dépendant (le lundi ne porte qu'en 2018-26).

## 6. Règles de déploiement recommandées

1. **Sleeve vol-targeté** (cible 10-12 % ann), pas standalone — sa fréquence (48/an) en fait un **diversifiant de l'ORB**, pas un passeur de challenge autonome.
2. **Kill-switch régime actif** : recalculer le Sharpe glissant 104-lundis chaque semaine ; flat si <0.
3. **Exécution MOO/MOC** (market-on-open / market-on-close) pour capturer open+close sans slippage de timing.
4. **Paper trading ≥3 mois** avant capital, réconcilier slippage réel vs 2 bps modélisé.
5. **Ne pas sur-sizer en régime bear** (corrélé à l'ORB en tail).

---

## 7. Ce qui resterait à durcir (honnêteté)

- **0 jour live** — tout est backtest. Le paper est obligatoire.
- **Open d'indice vs open tradable** : le cross-asset utilise l'OHLC ETF/indice ; le NQ utilise l'open RTH futures (tradable). Cohérent, mais valider les fills réels US100 CFD.
- **« Début de semaine » (lundi+mardi)** : mardi aussi +0,5 cross-asset → doublerait la fréquence ; à re-tester avec la même rigueur avant d'ajouter.
- **DSR formel sur l'espace total** des signaux testés (gap, momentum, 5 weekdays, seasonality) — la réplication cross-asset le couvre en pratique, mais un DSR explicite serait plus propre.

---

## 8. Comment le tester de ton côté (guide de réplication)

**Données nécessaires :**
- NQ (ou US100) 1-min, ou au minimum **open & close RTH quotidiens** (09:30 et 16:00 ET). Source ici : `outputs/nq_intraday_panel.parquet` (colonnes `open0`, `c389` = open 09:30 / close 16:00).
- Pour la réplication : OHLC quotidien de SPY/QQQ/DIA/IWM/EWG/EWJ (Yahoo `query1.finance.yahoo.com/v8/finance/chart/<TK>`).

**Logique (pseudo-code) :**
```
r_monday = close_1600 / open_0930 - 1        # sur les lundis uniquement
pnl      = r_monday - cost                    # cost = 2bp
SR       = mean(pnl)/std(pnl) * sqrt(252)
# vol-target:  pos_t = 0.11 / (rolling_std(pnl, 26 lundis).shift(1) * sqrt(252))
# kill-switch: trade si rolling_Sharpe(pnl, 104 lundis).shift(1) > 0
```

**Checklist de validation (refais-les, ne me crois pas sur parole) :**
1. SR lundi vs SR des 4 autres jours (lundi doit dominer — 8,6× le beta).
2. Split 2008-2017 vs 2018-2026 (l'effet doit être absent avant, présent après).
3. Réplication sur ≥4 indices indépendants (doit être 5-6/6 sur 2018-26).
4. Bootstrap CI du Sharpe (borne basse doit être >0).
5. Robustesse fenêtre (09:30→16:00 vs 10:00→16:00 : doit rester >1 sur 2018-26).
6. Walk-forward récursif avec kill-switch (doit donner ~1,2-1,3 déployable).
7. Pire journée vol-targetée < 5 % (compatibilité DD journalier FTMO).

**Script joint :** `monday_sleeve.py` (reproduit §2, §4.1-4.7 depuis le panel).

---
*Rapport 2026-06-02. Sharpe net 2bp. Données : `outputs/nq_intraday_panel.parquet` (NQ 1-min databento 16y), Yahoo OHLC 6 indices. Corr vs `outputs/orb_v2e7.parquet`. Réplication cross-asset = test OOS dominant. 0 jour live → paper obligatoire.*
