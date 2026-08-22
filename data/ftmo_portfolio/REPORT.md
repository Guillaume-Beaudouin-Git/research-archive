# Portefeuille FTMO 2-Step — Rapport final de mission
*2026-06-10 · Compte $10k · Mandat : p(pass) > 50% en ≤ 6 mois · Simulateur exact M5, coûts mesurés, 635 cohortes historiques 2013-2026*

> **⚠⚠ AMENDÉ PAR L'AUDIT RISK QUANT (voir AUDIT.md) — verdict final AUDITÉ :
> p = 45.8%, IC95 [30.6 ; 58.9] (IS 25.5% / OOS 67.1%).**
> Le 50.2% de l'itération 2 est rétracté : un trou de données US100/GER40 2018-2021
> (breaker aveugle) et le coût ORB uniforme gonflaient l'IS de ~10 pts. La règle
> d'abandon (+12 pts, §9.2) et la structure du book survivent à l'audit (causalité,
> comptabilité, sélection : PASS). Les §1-8 documentent l'itération 1.

---

## 1. Verdict (itération 1 — amendé par §9)

**La cible p(pass) > 50% en ≤ 6 mois N'EST PAS atteinte sur la base honnête (full-sample) :**

| Métrique (config finale, $10k, règles exactes) | Valeur |
|---|---|
| **p(funded ≤ 6 mois, retries inclus) — pooled 2013-2026** | **38.1%** — IC95 block-bootstrap **[25.4% ; 48.8%]** |
| p(funded ≤ 6 mois, 1 essai) — pooled | 36.2% |
| Sous-période 2013-2019 (régime chop/ZIRP) | 24.3% |
| Sous-période 2020-2025 (design gelé sur IS = vrai OOS) | **52.6%** |
| **p(funded ≤ 18 mois, retries)** | **56.0%** |
| Stress swap ×1.5 | 34.6% |
| Stress spread ×2 | 33.9% |
| Coût de la quantization lots $10k (vs positions continues) | −1.1 pt |
| Temps médian de passage (quand pass) | ~85-90 jours |

La borne supérieure de l'IC95 (48.8%) reste sous 50% : le verdict n'est pas un effet d'échantillon.
La cible EST atteinte (a) en relâchant l'horloge (~18 mois → 56%), ou (b) conditionnellement à la
persistance du régime post-2020 (52.6%) — un conditionnement **non exploitable** : la prédictabilité
du régime a été falsifiée par l'archive (ORB_regime_2026-06 : aucun prédicteur ne passe les gates,
t_HAC max 0.56, R² < 2% ; auto-corrélation mensuelle légèrement **négative**).

**Mise à jour du mur canonique :** l'ancien programme concluait ~33% (mono-stratégie, sans limite de
temps, coût idéalisé 2 bps). Ce travail établit **38% AVEC le mur des 6 mois**, coûts réels mesurés,
règles exactes au M5, et quantization $10k — et ~56% à 18 mois. Le portefeuille multi-sleeves + la
mesure des coûts ont réellement déplacé le mur ; ils ne le franchissent pas à 6 mois.

---

## 2. Le book final (gelé)

4 sleeves décorrélés (corrélations croisées ≈ 0-0.15), coûts réels par instrument×direction :

| Sleeve | Spec (archive-validée, non re-minée) | SR net full | SR net 2019+ |
|---|---|---:|---:|
| **Or trend** | TSMOM blend {60,120,250}, θ=0.34, carry-adj, vol-target 10%, XAUUSD | 0.35 | 0.47 |
| **J1** | USDJPY TSMOM 12-1 long-only, vol-target 10% | 0.43 | 0.42 |
| **Overnight midweek** | Long US100+GER40, nuits lun+mar (sessions cash exactes 15:30/22:00, 09:00/17:30 CET), net swap+spread | 0.66 | 0.46 |
| **ORB V2+E7** | Opening-range breakout 30min US100, ledger canonique 4013 trades re-pricé au coût CFD **mesuré** (1.5 bps RT all-in) | 0.40 | 0.99* |

*\*concentration de régime documentée ; full-sample = chiffre de référence (leçon canonique).*

**Découverte clé (réouverture légitime de l'ORB)** : le spread US100 CFD à l'auction 15:30 CET,
**mesuré sur 518 jours** (M1 calibré 2024-2026) = **0.47-0.55 bps médian, p95 0.64** — contre
l'hypothèse 6-10 bps qui avait tué l'intraday. mean_R(E7) @1.5 bps = **+0.0305** (n=4013) ; encore
positif @2.5 bps (+0.008). Condition de réouverture #2 du canonique remplie par mesure (caveat : feed
Dukascopy ≠ feed FTMO garanti → vérification démo = pré-condition de déploiement).

**Rejets re-confirmés aux coûts réels** (négatifs rigoureux) : FX 10-paires two-sided (SR −0.36 à
−0.18 même swap-gated — confirme A1), equity trend two-sided (−0.4, confirme oxfordstrat 30/30
DISCARD), énergie trend MÊME long-only-avec-crédit-de-swap (+0.05 ≈ 0), **crypto trend exclu**
(2019-2026 cumul ≈ 0%, coût 18.5 bps RT + swap −8.2 bps/nuit), softs (spreads CFD 144-1190 bps
prohibitifs + granularité), TSMOM multi-FX générique.

---

## 3. Moteur de risque (la policy, optimisée IS 2013-2019, validée OOS 2020-2025)

| Composant | Réglage final | Justification mesurée |
|---|---|---|
| Vol multiplier | 2.0× | Frontier IS : pass plafonne 45-47% à 1.5-2.5× ; busts explosent ≥3× |
| Cap notionnel/jambe | 1.5× equity | La cascade vol-target gonflait p95=2.85×/max 9.6× → bust_daily 11%→2.5% |
| Breaker intraday | flatten si room < 30% du budget daily | Simulé au M5, fill au bar suivant |
| Taper floor | linéaire sous 4% de distance au floor, **ORB inclus** | Sans : l'ORB $-fixe bascule les cohortes stagnantes |
| Pacing horloge | scale ×[0.8 ; 2.0] selon retard sur le glide-path | Convertit les timeouts P2 : 54.7%→23.5% |
| Phase 2 | 0.8× du risque P1 + pacing | P2 chaude (1.2×) bustait 33% des séquences |
| Réalisation P&L | **NE PAS réaliser quotidiennement** | Contre-intuitif mesuré : le buffer de gains flottants (balance < equity) protège la règle daily (bust 11%→17.5% si réalisation quotidienne) |
| Weekend | **rester en position** | Flat weekend = perte de drift > protection gap (pass −3.4 pts) |
| Quantization | lots exacts (0.01), min/step specs | Coût mesuré : −1.1 pt seulement à $10k |

Modes d'échec (config finale, P1) : pass 46.5%, timeout ~42% (régimes sans drift — **incompressible
par le levier**, le goulot est l'edge), bust_daily ~7%, bust_floor ~3-5%. Les retries n'apportent que
+2-3 pts : les busts sont rares et les timeouts consomment l'horloge entière.

---

## 4. Coûts (le paramètre qui décide — L33, désormais mesuré)

| Classe | RT all-in mesuré (spread méd. + slip + comm.) | Swap (modèle calibré, variable dans le temps) |
|---|---|---|
| FX majors | 1.1-3.1 bps | markups 1.4-3.5%/an par côté sur le différentiel 3m (10 devises, 2005-2026) |
| Indices | 2.2 bps (auction 15:30 : 0.5 bps !) | ancre mesurée US100 −662.4 pts = −$6.62/nuit exact |
| XAU | 1.8 bps | −2.0 bps/nuit long (markup 3.8%) |
| Oils | 8.2-8.5 bps | long +3/+4 bps/nuit (crédit), short −14/−19 |
| Crypto | 18.5 bps | −8.2 bps/nuit (−30%/an, fourni utilisateur) |

Le modèle de swap reproduit exactement les specs broker de juin 2026 et varie avec les régimes de
taux historiques (ZIRP 2010-2021 ≈ financing quasi nul — ce qui explique que le trend book net
historique soit meilleur que les bornes pessimistes du dossier TSMOM).

---

## 5. Pourquoi pas plus ? (la décomposition du mur)

1. **Mur Sharpe sous horloge** : passer +10% puis +5% en ≤182 jours avec p>50% exige un drift
   médian ≥ ~0.12%/jour à vol contenue (daily 5%/floor 10%) ⇒ SR ≳ 1.5 tenu sur la fenêtre.
   Book réel : SR ~0.75-0.85 stable. Le levier ne crée pas de drift : il accélère la résolution
   (pass plafonne, busts montent).
2. **~42% de timeouts structurels** : les semestres sans trend or/jpy/NQ ne paient aucune policy.
   La prédictabilité de ces régimes est falsifiée (archive + ce travail).
3. **Les retries n'aident qu'après bust rapide** — or le design optimal minimise les busts.
   Paradoxe mesuré : un book "sûr" perd l'optionalité de re-roll.
4. **Épuisement des sleeves validés** : tout edge additionnel exigerait du mining frais
   (dette de tests multiples → claim invalide par la charte) ou un autre container.

---

## 6. Si vous tentez quand même (protocole de déploiement)

Espérance honnête : ~38% de proba de funding par fenêtre de 6 mois (fee ~€89/essai, remboursée si
funded), ~56% à 18 mois en ré-essayant. EV du ticket à éclaircir vs vos objectifs.

1. **Compte** : 2-Step $10k, **acheter Swing** (irréversible Standard→Swing ; pendant l'évaluation
   les restrictions ne s'appliquent pas, mais le book financé tiendra des positions multi-semaines).
2. **Pré-conditions de mesure (≥3 semaines démo)** : spread US100 à 15:30:00/15:33/16:00 CET
   (seuil : ≤1.5 bps RT all-in sinon ORB off) ; swaps réels XAU/USDJPY/US100/GER40 vs specs ;
   slippage des market orders du breaker.
3. **Exécution** : EA MT5 — rebalance 22:05 CET, jambes overnight 17:35/22:05→09:00/15:30,
   breaker M5, taper/pacing/glide selon `simulator.py` (la spec exécutable EST le code).
4. **Kill criteria** : spread mesuré > 2× hypothèse ; swap > 1.5× modèle ; 3 mois glissants de
   book < −6% hors busts.

---

## 7. Reproduction

```
ftmo_portfolio/
  config.py            # règles FTMO verrouillées (sources officielles 2026-05/06) + univers
  costs.py             # moteur swap/spread/commission, calibré sur ancres mesurées
  dataio.py            # M1 true-UTC -> barres daily CE(S)T + M5 (28 instruments)
  research_panel.py    # panel maître 2000-2026 + tables de coûts
  sleeves.py           # moteurs de signaux (TSMOM blend, J1, overnight)
  prep_signals.py      # poids quotidiens du book (cap 1.5x/jambe) + flag overnight
  simulator.py         # simulateur exact M5 par segments : règles, comptabilité balance/equity,
                       #   quantization, breaker, taper, pacing, funnel 2 phases + retries
  run_phase0/1/1b/1c/3 # pipeline complet ; outputs/ = tous les CSV cités ici
```
Chaque chiffre de ce rapport est régénérable par les scripts ; aucun chiffre à la main.

## 8. Leçons banquées (candidates au journal)

- **L-mesure-avant-verdict** : l'ORB était mort sur une hypothèse de coût (6-10 bps) ; la mesure
  (0.5 bps à l'auction) le ressuscite en sleeve d'appoint. Symétriquement, le swap "tailwind +30% du
  SR" de J1 (proxy ^IRX) est en réalité un léger coût net aux swaps broker réels. *Mesurer change le
  signe dans les deux sens.*
- **L-buffer-flottant** : sous une daily-loss ancrée balance, NE PAS réaliser quotidiennement ;
  le flottant positif est un coussin réglementaire gratuit (mesuré : +6 pts de bust si réalisation).
- **L-cap-notionnel** : tout vol-targeting cascadé doit être cappé en notionnel — les régimes calmes
  fabriquent du levier caché (p95 2.85×, max 9.6×) que la barrière punit.
- **L-retry-paradox** : minimiser les busts détruit la valeur des retries ; sous horloge, l'optimum
  global n'est pas l'optimum par essai.
- **L-clock-vs-container** : le même book passe de 38% (6mo) à 56% (18mo) — l'horloge externe est
  une contrainte plus chère que la barrière elle-même. *(Amendé par §10 : à design optimal, c'est
  l'inverse — l'horloge courte force le design de variance qui domine partout.)*

---

# 10. MANDAT SPRINT 2 MOIS (2026-06-10, nuit) — LE GATE EST FRANCHI

*Directive MD : p(pass) > 50% en ≤ 61 jours. Tout sur stack audité (données réparées, ORB era-costed).*

## 10.1 Verdict

| Métrique — design SPRINT (vm 14, P2 ×1.2, abandon 5j, breaker/taper/pace inchangés) | Valeur |
|---|---|
| **p(funded ≤ 61 jours, retries) — pooled 2013-2026, 650 cohortes** | **59.5%** — IC95 **[51.7% ; 67.2%]** |
| **P(p_vrai > 50%)** | **0.99** ✓ |
| IS 2013-19 (design gelé dessus) / OOS 2020-26 | 59.1% / **60.0%** (zéro décay) |
| Stress swap ×1.5 / spread ×2 | 58.4% / 54.7% |
| Temps médian de funding / essais moyens / budget fees | ~26-30 j / 2.62 / ~€233 (remboursées si funded) |
| **Option comptes parallèles** (A = book complet ; B = overnight+ORB seul, corr mesurée 0.08) | **p(au moins un) = 80.6%**, fees ×2 |
| **Le même design sous le mur 6 mois** | **90.9%** (vs 45.8% du design prudent audité) |

## 10.2 Pourquoi ça marche (la mécanique, honnêtement décomposée)

À 61 jours, aucun drift réaliste ne traverse +15.5% : **le design optimal est une machine de
variance séquencée** — vol très haute (notionnels jusqu'à ~20× par jambe, exécutables : ~0.5 lot
or, marge ~5% à 1:100), pertes journalières cappées par le breaker M5, busts/abandons rapides
(5 j), retry immédiat, P2 chaude (barrières +5/−10 asymétriques : la vol y est quasi gratuite).
Les retries composent parce que les outcomes sont dominés par le tirage de variance (frais à
chaque essai), plus par le régime — contrairement au design de drift où le régime verrouillait.

**Décomposition placebo (hygiène canonique)** : un book ANTI-edge (signaux inversés) à la même vol
passe **47.1%** — le container (règles + séquencement + asymétrie P2) porte ~47 pts ; l'edge réel
ajoute **+12 pts** → 59.1/59.5%. Le claim n'est PAS "alpha énorme" ; c'est "ingénierie de barrière
+ edge modeste, mesurés proprement". Sans aucun edge non plus ça ne passe pas : beta constant
non-managé à cette vol = 0.0% (la gestion par jambe/breaker est la condition de survie).

## 10.3 Risques spécifiques au design sprint (à lire avant tout déploiement)

1. **Clause 7.3 FTMO ("gambling-like behaviour")** : un style à ~20× notionnel séquencé sur 2-3
   comptes peut attirer l'attention du risk desk. Défendable (multi-positions, stops, breaker,
   risk-management systématique ≠ all-in unique) mais **risque non quantifiable en backtest**.
   Mitigation : vm 10-12 (p ≈ 53-56%) si l'on veut un profil plus discret.
2. **Slippage aux notionnels hauts** : fills M5-close en sim ; stress spread ×2 → 54.7% le borne
   partiellement. Mesure démo obligatoire (inchangée).
3. **Gaps overnight/weekend à 20×** : busts-floor plus fréquents — c'est DANS le design (retry),
   mais psychologiquement brutal : ~65% des tentatives meurent, souvent en quelques jours.
4. Compte d'essais policy de l'itération sprint : ~18 cellules, gelé sur IS, validé OOS sans décay.

## 10.4 Recommandation

Mandat 2 mois : **GO au point de design vm 14** (59.5% [51.7 ; 67.2]), ou **vm 12** pour le profil
compliance-prudent (~55%), ou **2 comptes parallèles** pour 80.6% à fees doubles. Et noter que le
même design résout le mandat 6 mois à 90.9% — l'ancien design de drift est retiré.

---

# 11. ÉCONOMIE COMPLÈTE DE L'OPÉRATION (questions MD, 2026-06-10)

*Hypothèses : fee $10k 2-step = €89 ≈ $96 ; split trader 80% ; fee remboursée au 1er payout ;
extraction funded simulée sur horizon 2 ans (TRONQUÉ = conservateur, 97-100% des comptes prudents
encore vivants à l'horizon) ; retraits mensuels du réalisé ; scaling plan ignoré (upside).*

## 11.1 Combien d'essais pour 95% ?

| Mur calendrier | p(funded) | essais utilisés (espérance) | fees espérées |
|---|---:|---:|---:|
| 61 j (2 mois) | 59.5% | 2.62 | ~$252 |
| 182 j (6 mois) | 90.9% | 3.50 | ~$336 |
| **270 j (~9 mois)** | **95.8%** | **3.91** | **~$375** |

→ **~4 essais utilisés en espérance (8-10 disponibles) et ~9 mois de calendrier pour 95%.**

## 11.2 Un seul essai — le chiffre honnête

Le frontier single-attempt est PLAT et plafonne ~28-30% quel que soit le réglage :

| Config | p(pass, 1 essai) |
|---|---:|
| vm 2 (prudent), 61 j | 14.2% |
| vm 6, 61 j | 22.8% |
| **vm 10 (optimum single), 61 j** | **28.2%** |
| vm 14 (sprint), 61 j | 27.6% |
| vm 10, 182 j | 29.5% |

**p(pass | 1 essai) ≈ 28%, point final.** Le passage au-dessus de 50% est STRUCTURELLEMENT un
produit du séquencement — pas de la triche : c'est le design du produit FTMO lui-même (fee par
essai, remboursée si succès — la firme monétise exactement ce re-essai).

## 11.3 L'EV est-elle positive ? De combien ?

Extraction funded (portefeuille_funded vm 1.0, 2 ans tronqués, brut avant split) :
IS $971 / OOS $2,691 / **pooled ≈ $1,684** (médiane OOS $2,120, p10 $73, p90 $5,185, busts 0-3%).

| Campagne (sprint → funded prudent) | E[fees] | p(funded) | E[valeur si funded]* | **EV** |
|---|---:|---:|---:|---:|
| 2 mois | $252 | 59.5% | $1,443 | **+$607** |
| ~9 mois (95%) | $375 | 95.8% | $1,443 | **+$1,008** |
| Bornes 2 mois (extraction IS-only / OOS-only) | | | | +$267 / +$1,086 |
*refund $96 + 0.8 × extraction pooled.*

**EV par essai = +$232** (seuil de rentabilité : p_essai × valeur > fee → 0.28 × $1,443 = $404 ≫ $96).
ROI sur fees espérées ≈ **2.4×** (2 mois) à **2.7×** (9 mois). L'EV est positive, robuste aux bornes,
et TRONQUÉE par l'horizon 2 ans (la vraie queue de vie des comptes prudents est plus longue).

## 11.4 Le switch funded-prudent : la décision qui porte toute l'EV

| Book gardé une fois funded | E[extraction 2y] | médiane | bust % | vie médiane | EV campagne 2 mois |
|---|---:|---:|---:|---:|---:|
| **Sprint vm 14 (inchangé)** | $419 | **$0** | **59%** | **27 j** | **≈ +$4 (zéro)** |
| **portefeuille_funded vm 1.0** | **$1,684** | $2,120 (OOS) | 0-3% | >504 j (vivant) | **+$607** |

**portefeuille_funded (spec gelée)** : le book audité inchangé (or trend + J1 + overnight midweek +
ORB era-costed), vm 1.0, breaker 0.30, taper 0.02, pace OFF, glide OFF, abandon OFF, retraits
mensuels du réalisé, compte Swing (positions weekend + news OK — choix d'achat déjà imposé).
IS-optimum sur {0.5, 0.75, 1.0, 1.5} : vm 1.0 ($971), validé OOS ($2,691). À vm 14 la machine de
variance qui GAGNE le challenge DÉTRUIT le compte funded — l'asymétrie des deux phases du jeu est
totale : sprint pour franchir la barrière, prudence pour la rente. **C'est le switch qui transforme
une opération à EV nulle en +$607/campagne.**

*Directive MD : franchir 50% en 6 mois ; ML autorisé sous condition de rigueur.*

## 9.1 Verdict final amendé

| Métrique (design final : + règle d'abandon, taper 0.02) | Valeur |
|---|---|
| **p(funded ≤ 6 mois, retries+abandon) — pooled 2013-2026** | **50.2%** — IC95 block-bootstrap **[35.6% ; 63.1%]** |
| P(p_vrai > 50%) (bootstrap) | 0.46 — **au niveau de la barre, pas au-dessus avec confiance** |
| Sous-période 2013-2019 / 2020-2025 (design-OOS) | 35.7% / **65.5%** |
| Essais moyens par fenêtre / budget fees | 1.62 / ~€144 (remboursés si funded) |
| Stress swap ×1.5 / spread ×2 | 47.4% / 46.4% |
| Horloge 12 mois | **69.5%** |

## 9.2 D'où vient le gain (+12 pts) — PAS du ML

**Diagnostic structurel** : les "timeouts" de l'itération 1 mouraient à médiane **−8.9%** d'equity —
épinglés au-dessus du floor par le taper lui-même (positions → 0 près du floor : ni bust ni recovery
= **état zombie policy-induit**, 42% des tentatives). Le "mur des régimes sans drift" était pour
moitié un artefact de mon propre governor.

**Fix : règle d'abandon** — equity < floor + 2% pendant 8 jours consécutifs ⇒ abandonner le compte
et relancer un challenge avec l'horloge restante (opérationnellement trivial ; le bust/abandon
redevient une option et les retries reprennent de la valeur : 1.0 → 1.62 essais/fenêtre).
IS +11.4 pts, OOS +12.9 pts, insensible sur la mini-grille {vm, taper} (3 cellules).

## 9.3 Les tentatives ML/conditionnement — quatre falsifications propres

| Tentative | Spec (pré-enregistrée) | Résultat | Verdict |
|---|---|---|---|
| Meta-labeling ORB | hérité de l'archive avant build | F1/ttb = **look-ahead short confirmé** par leur bughunt (Δ corrigé −0.025) ; signature 3-var sous quarantaine pré-enregistrée post-2026-07 | **Foreclos — non construit** (re-miner du falsifié = violation de charte) |
| Ledgers breakout ×8 re-pricés | comme la résurrection ORB | phase4 delay-1 : tous ≈ 0 (artefact de fill intrabar, cohérent re-audit S002) | **Foreclos** |
| Governor vol-prédictif | Ridge HAR+VIX, walk-forward purgé, refit annuel | corr OOS 0.238 **< baseline naïf RV5 0.265** ; et l'overlay RV5 lui-même : **−13.5 pts** IS (book régime-sparse : \|r\| élevé = périodes où l'edge paie) | **Rejeté ×2** |
| Start-gate (book 63d > 0) | 1 condition, 1 test | lift pooled +2.4 pts, IC95 [−15.4 ; +23.3], signes opposés IS/OOS | **Rejeté** (le prior "bruit blanc" de l'archive tient) |
| Skip overnight si VIX>30 | 1 condition, 1 test | IS −4.6 / OOS +1.9 — incohérent | **Rejeté** (règle de consistance) |

Compte d'essais de l'itération chargé au verdict : 8 tests de policy/conditionnement, 1 seul shippé
(l'abandon — issu d'un diagnostic, pas d'une sélection). La pression de sélection sur le 50.2% est
faible ; l'IC95 reflète l'incertitude d'échantillon réelle.

## 9.5 → voir §10 : le mandat 2 mois a produit un design qui domine aussi celui-ci.

## 9.4 Lecture honnête pour décision

Le point estimate franchit la barre (50.2%) ; la confiance statistique que p_vrai > 50% n'est que de
46%. Framing opérationnel : **si les 6 prochains mois ressemblent au régime macro post-2020 → ~65% ;
s'ils ressemblent au chop 2013-2019 → ~36% ; sans information de régime (falsifiée) → ~50%.**
À 12 mois de patience, 69.5%. Les pré-conditions de déploiement du §6 restent inchangées
(spread/swap démo, EA, kill criteria) + une : implémenter l'abandon à J+8 sous floor+2% sans état d'âme.
