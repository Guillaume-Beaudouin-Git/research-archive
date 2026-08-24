# Postmortem — H31 CS-FS Delta-Neutral Carry
## Test #160 | Verdict : RESEARCH_FAIL | PROPFIRM_FAIL

*Branche : `claude/h31-cs-fs-dn-test-160` | Date : 2026-05-28*  
*Backtest : 2024-01-01 → 2026-05-05 (856 jours, crypto 365j/an)*  
*Univers : dynamique point-in-time, N=22 au départ → N≈170+ à la fin*

---

## 1. Résultats

| Métrique | Valeur | Gate | Statut |
|----------|--------|------|--------|
| Sharpe net (ann) | −0.804 | > 0.7 | ✗ FAIL |
| Max Drawdown | −69.9% | > −25% | ✗ FAIL |
| HAC t-stat (lag-6) | −1.198 | > 1.5 | ✗ FAIL |
| WF folds positifs | 1/4 (25%) | > 50% | ✗ FAIL |
| HLZ t_required (n=41) | 6.23 | — | ✗ FAIL |
| DSR | 0.000 | — | ✗ FAIL |
| Corr vs BTC (proxy A) | 0.038 | — | delta-neutral ✓ |

**Rendement total** : −56.9% sur 2.34 ans  
**Rendement annualisé** : −29.2% | **Vol annualisée** : 36.3%

### Yearly breakdown
| Année | Sharpe OOS |
|-------|-----------|
| 2024 | −1.790 |
| 2025 | +0.649 |
| 2026 (partiel) | −1.138 |

### WF detail
| Fold | Sharpe OOS |
|------|-----------|
| Fold 1 | −1.904 |
| Fold 2 | +2.273 |
| Fold 3 | −1.851 |
| Fold 4 | −0.066 |

---

## 2. Diagnostic de cause : pourquoi H31 échoue

### 2.1 Le carry rate est dominé par le return de prix

La contribution du funding à la P&L brute : **5.1%**. Les 94.9% restants viennent des
price returns, qui sont **négatifs** en moyenne pour cette stratégie.

Le coût de transaction : 23.4% du notionnel total sur 856 jours (≈10%/an).  
Mais même en enlevant les coûts, le Sharpe gross resterait largement négatif car le
signal prix va dans le mauvais sens.

### 2.2 Signal directionnellement inversé en marché bull

La logique carry (pré-spec) :
- Long : funding_z le plus bas (funding très négatif = shorts paient les longs)
- Short : funding_z le plus haut (funding très positif = longs paient les shorts)

En 2024, le cycle crypto était haussier (BTC +120% en 2024). Les assets avec funding très
positif sont ceux en tendance haussière forte → **shorter ces assets en 2024 est destructeur**.
Les assets avec funding très négatif sont ceux en correction ou en tendance baissière →
**les acheter en 2024 est également destructeur**.

Le carry est correct en théorie : on reçoit des fonds des deux côtés. Mais le magnitude
du carry (5.1% du P&L) est écrasée par les price returns directionnels.

### 2.3 Le funding signal est un proxy de momentum inversé

Funding rate élevé → bulls surreprésentés → asset en momentum positif → stratégie le **shorte**.  
Funding rate négatif → bears surreprésentés → asset en momentum négatif → stratégie le **achète**.

H31 est structurellement une stratégie de mean-reversion sur momentum cryptographique. 
En 2024-2025 (forte tendance directionnelle), le momentum domine et la mean-reversion échoue.

### 2.4 Seul fold positif : Fold 2

Le fold 2 (≈ milieu 2024) correspond approximativement à la période de consolidation après
le rally BTC d'avril 2024 (ATH $73K) et avant le rally post-élection novembre 2024. Dans
les marchés range-bound, le carry contrarian peut fonctionner. Mais ce n'est pas un signal
robuste sur cycle complet.

### 2.5 Coût de transaction excessif

23.4% de notionnel en 2.34 ans = ~10%/an de drag sur une stratégie qui tourne 20-21 positions
par side. Avec rebalancement daily et quintiles mobiles, les rotations sont fréquentes. Le
coût HL taker (0.045% RT) est bien plus bas que Binance (0.17%), mais reste trop élevé pour
cette fréquence de rotation sur des rendements carry de ~1-2%/an bruts.

---

## 3. Comparaison avec PMR Basis (test précédent H31-adjacent)

| Métrique | PMR Basis (Binance, 2021-2024) | H31 CS-FS (HL, 2024-2026) |
|----------|-------------------------------|---------------------------|
| IC t_HAC | −2.86 (PASS à 3 jours) | −1.198 (FAIL, signe négatif) |
| Coût RT | 0.17% (Binance taker) | 0.045% (HL taker) |
| Verdict cost | FATAL (178%/an vs 16-20% gross) | FATAL (10%/an, signal négatif) |
| N events/yr | 912 → coût écrasant | ~7,500 rebalances → coût élevé |

La différence : PMR avait un IC positif (t=−2.86 = signal réel en direction contraire de
l'hypothèse initiale), H31 n'a pas d'IC détectable (t=−1.198 noise).

---

## 4. Note méthodologique : HLZ t_required

La pre-spec avait estimé t_required ≈ 3.18. Le calcul exact avec la formule HLZ implémentée
donne **6.23** pour n=41. Cette discordance provient du facteur multiplicateur √(log n) :
avec n=41, log(41)=3.71, √3.71=1.93. La pre-spec avait peut-être oublié ce multiplicateur
ou utilisé une formule simplifiée. Cela ne change pas le verdict : t_HAC = −1.198 est
négatif et échoue tout seuil raisonnable (même t > 0).

---

## 5. Verdict final

**RESEARCH_FAIL** — Signal négatif (t_HAC = −1.198), MaxDD −69.9%, WF 1/4.  
**PROPFIRM_FAIL** — Non pertinent (strategy non viable).

H31 CS-FS Delta-Neutral Carry est **archivé** comme hypothèse falsifiée.

### Ce que le test établit :

1. **L'IC du signal funding_z CS est négatif** sur la période 2024-2026 (bull crypto). Le
   signal est directionnellement inversé par rapport à son mécanisme supposé (carry receive).

2. **Le carry est réel mais marginale** : 5.1% de la P&L brute, insuffisant pour compenser
   les price returns adverses et les coûts.

3. **Corrélation avec BTC (proxy A) = 0.038** : la stratégie est effectivement delta-neutral
   en termes de prix. C'est le seul critère structurellement confirmé.

4. **L27 s'applique** : avec n=41 (HLZ) et N_mod=0, DSR=0 même si le Sharpe était positif.
   La voie DSR ne se débloque que par pre-registration dès le premier test de la famille.

---

## 6. Variants non testés (conformément à la règle des 3 modifications max)

Aucun variant n'est proposé. H31 échoue sur la direction du signal, pas sur des paramètres
ajustables. L'inversion du signal (long top quintile, short bottom) testerait une hypothèse
différente (H41 : momentum carry). Ce serait un test #161 avec une pré-spécification distincte.

---

*Archivage : déplacer `h31_cs_fs_dn/` → `Crypto/research/archived/h31_cs_fs_dn/` après review*
