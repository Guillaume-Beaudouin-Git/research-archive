# AUDIT RISK QUANT — Book FTMO 2-Step (post-itération 2)
*2026-06-10 · Audit indépendant de la chaîne complète : données → coûts → signaux → simulateur → claims.
Méthode : revue de code systématique + tests adversariaux + contrefactuels + forensique comptable.*

---

## VERDICT D'AUDIT

> **Le claim d'itération 2 (p = 50.2%) est RÉTRACTÉ.**
> Deux findings matériels (un trou de données critique, un modèle de coût ORB trop optimiste sur
> l'ère ancienne) gonflaient l'IS. **Headline audité et corrigé : p(funded ≤ 6 mois) = 45.8%,
> IC95 [30.6% ; 58.9%], P(p_vrai > 50%) = 0.24.** Sous-périodes : IS 2013-19 = 25.5%,
> OOS 2020-25 = 67.1%. La structure du book et le simulateur sortent par ailleurs blanchis
> (causalité PASS, comptabilité PASS, sélection de composition OOS-neutre).

---

## 1. Findings

| # | Sévérité | Domaine | Finding | Statut |
|---|---|---|---|---|
| **F1** | **CRITIQUE** | Données | **US100 M1 : 1 bar/jour sur 2018-2020** (stubs daily, 0 bar à 15:30 ; GER40 : trou mi-2019→2021). Conséquences en sim : breaker et règle daily **aveugles intraday** 3 ans sur ces jambes, jambe overnight transformée en hold 48h involontaire à granularité daily. **Gonflait l'IS de +9.2 pts.** Cause racine : splice deep-history — la plage "MT5 authoritative" pour US100 ne contenait que des bouchons quotidiens sur 2018-2020, et le backfill Dukascopy ne remplit que strictement avant/après la plage existante. | **CORRIGÉ** : proxy NQ databento M5 (corr 0.997 validée archive) splicé sur les 967 jours ouvrés du trou, ancré en continuité (seam unique 0.35%, 1 nuit, notée) ; GER40 masqué NaN sur son trou (jambes auto-neutralisées via quantize-guard, ffill bloqué par nan_mask). |
| **F2** | **MATÉRIEL** | Coûts | **Coût ORB uniforme 1.5 bps anachronique** : spread d'auction US100 mesuré par année = 4.3 bps (2013), 3.8 (2014), 1.5-2.6 (2015-17), 0.4-0.6 (2021+). En coût d'époque, mean_R ORB 2013-19 = **−0.057** (négatif !) vs +0.099 en 2021+. Gonflait l'IS de +1.0 pt. | **CORRIGÉ** : ledger re-costé par année (`orb_e7_Rera.parquet`) ; le sleeve ORB n'a d'EV positive que dans l'ère moderne des spreads serrés — fait documenté au rapport. |
| **F3** | PASS | Causalité | **Delay-test au niveau funnel** : anticausal −1j → aucune amélioration (48.1 = 48.1 : pas de leak caché) ; +1j → −2.8 pts, +3j → −11.8 (dégradation graduelle = signal lent réel). Chaîne WT : info ≤ minuit J−1 appliquée à 22:05 de J = **causal avec 22h de marge** (l'alternative WT[i+1] aurait été un look-ahead de 2h — vérifié non utilisée). ORB posté à 22:05 ≥ résolution 22:00 ✓. ON = calendrier pur ✓. | — |
| **F4** | PASS | Sélection | **Contrefactuel de composition** : la seule décision que les données IS-only auraient inversée (garder crypto) donne OOS 66.8% vs 67.1% — **OOS-neutre**, et pooled avec-crypto légèrement *supérieur* : la composition n'a pas été gamée sur l'outcome. Biais de sélection résiduel ≈ ≤0.5 pt. | — |
| **F5** | MINEUR | Modèle | (a) ordre intra-bar M5 : bust prioritaire sur breaker dans le même bar = conservateur ; (b) churn du zombie pré-abandon (open 22:05 → breaker-flatten) = coût réaliste, mécanisme correctement nommé **breaker-deadlock près du floor** (le taper n'était qu'aggravant) ; (c) WT=0 les jours fériés panel → churn mineur ; (d) approximation quanto USDJPY (~ret², négligeable) ; (e) DST : fenêtres US décalées 1h ~3 sem./an (bruit, pas de biais) ; (f) spreads swing par époque : or 1.4-1.7 bps (2014-18) vs 1.84 utilisé — sous-coût borné par le stress spread ×2 ; (g) lot-rounding par `round()` (overshoot symétrique possible, coût mesuré −1.1 pt). | Documentés |
| **F6** | NOTE | Conformité | Marge : gross max ~4× equity → marge requise « $400-800 sur $10k à 1:100 ✓. Min-trading-days : comptage conservateur (ouvertures only). Règle daily : ancre balance-minuit conforme au texte officiel, buffer de gains flottants vérifié conforme (equity = balance + flottant ± swaps − commissions). Swaps : signes/3x-day vérifiés en forensique (XAU mer. 3x ✓, −2.48 bps/nuit ✓). | — |

## 2. Headline corrigé et attribution

| | avant audit | après audit | Δ |
|---|---:|---:|---:|
| IS 2013-2019 | 35.7% | **25.5%** | −10.2 (data −9.2, era-cost −1.0) |
| OOS 2020-2025 | 65.5% | **67.1%** | +1.6 (réparation 2020-21 + coût moderne) |
| **Pooled** | 50.2% | **45.8%** | −4.4 |
| IC95 | [35.6 ; 63.1] | **[30.6 ; 58.9]** | |
| P(p_vrai > 50%) | 0.46 | **0.24** | |

Le mécanisme du gonflement IS : des données à 1 bar/jour rendaient **invisibles les breaches
intraday** (moins de busts détectés = pass fictifs), pas un look-ahead de signal.

## 3. Risques résiduels (non corrigeables en backtest)

1. **Feed FTMO ≠ feed Dukascopy/NQ** : spreads/exécution à re-mesurer en démo (pré-condition déjà au §6 du rapport — inchangée, renforcée).
2. **Proxy NQ sur 3 ans d'IS** : basis NQ/US100.cash (dividendes/financing) non répliquée intraday — neutre directionnellement, mais l'IS 25.5% porte cette approximation.
3. **Markups de swap constants dans le temps** : calibrés juin 2026, appliqués à l'histoire via les taux 3m — hypothèse raisonnable, non vérifiable rétroactivement.
4. **Une seule histoire** : le block-bootstrap quantifie l'erreur d'échantillonnage des cohortes, pas le risque de régime inédit.

## 4. Conclusion d'audit

Le book est **structurellement sain** (causalité, comptabilité, compliance, sélection) ; le
simulateur est conforme aux règles officielles ; mais les claims chiffrés pré-audit étaient
**gonflés par la qualité des données d'une sous-période**. Le chiffre défendable en comité :
**45.8% [30.6 ; 58.9] pooled — la barre des 50% n'est PAS franchie sur la base honnête** ;
elle l'est uniquement conditionnellement au régime post-2020 (67.1%, design-OOS, données saines
sur cette fenêtre) ou en relâchant l'horloge. Recommandation : si déploiement, le faire en
connaissance du chiffre pooled, avec les pré-conditions démo, et re-mesurer p après 2-3 fenêtres.
