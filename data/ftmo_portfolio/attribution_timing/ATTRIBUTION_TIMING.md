# SLEEVE ATTRIBUTION & START-TIMING — challenge book v2.1
*2026-06-10 · Moteur : cleanroom audit (stack gelé `audit_stack`-équivalent), micro-trade
day-counter ON partout. Baselines : étude 84.6% (runner cleanroom) / 85.1% (runner attribué) /
85.6% (grille step-1) — cross-check moteur auteur 83.5% (pas de micro-trade rule), tout ∈ ±1.5 pt.
CIs = block-bootstrap (blocs 10 cohortes step-7 / 65 cohortes step-1). N_eff affiché par bucket.*

## VERDICT (Q1/Q2/Q3)

**Q1 — Poids réalisés ≠ budgets spec.** Notionnel brut : **J1 51%** (16.3× equity quand actif —
la plus grosse jambe), overnight 26% (13.8× actif), or 21% (8.3×), **ORB 1.8%** (0.14×, ~6.5h/j).
Risque (part de variance du book) : **overnight 43%**, or 32%, J1 25%, **ORB 0.4%**. Marge
pré-cap : p50 21% / p95 61% / p99 79% / max 121% ; le cap 60% mord **5.3%** des rebalances
(trim médian ×0.87, proportionnel toutes jambes, ORB hors cap).

**Q2 — Le moteur, c'est l'overnight ; l'ORB est du lest (challenge).** Overnight = drift
**+$8.5/j** (~2× le drift book total $4.6/j) ET 1ère part de variance → LOO iso-vol
**−10.6 pts [−20.6;−1.1]**, seul retrait CI-significatif → **ablation pendante : KEEP**.
Or = moteur n°2 (+$4.4/j ; −9.7 pts no-rescale [−17.7;−1.7]). J1 = fournisseur de variance
DIVERSIFIANTE à drift négatif (−$8.6/j de saignée de re-trading quotidien à 16×eq) ; son
retrait est ~gratuit en p (−2.2 ns, EV +$8) mais re-leverager les autres ne le remplace pas
(iso-vol −5.2). **ORB : retrait = +3.7/+3.9 pts, EV +$74-79** — nuisance nette dans le
challenge ; sa valeur vit dans le funded (extraction −52% si mort, cf. audit). Flag-only ≡
retrait pour les 4 sleeves → **zéro valeur mécanique résiduelle** (la micro-trade rule couvre
tout le rôle compteur-de-jours).

**Q3 — Pas de fenêtre de départ exploitable : START ANYTIME.** 27 buckets pré-enregistrés
(H1-H5, grille step-1 n=3,223, p inconditionnel 85.6%) : max |z| = **1.70** (« démarrer en
régime ORB DÉFAVORABLE » 90.6% — sens anti-intuitif, cohérent avec l'alternance mensuelle ORB
+ ORB-nuisible) < barre de déflation **√(2 ln 27) = 2.57**. Aucun bucket ne survit ; EV
positif partout ($810-1,027). Recommandation : **démarrer n'importe quand** ; les retries
effacent le timing.

---

## P1 — Poids réalisés (tables/p1_realized_weights.csv, plots/p1_risk_shares_ts.png)

| sleeve | notional share | ×eq (moyen) | ×eq (actif) | risk share | drift $/j | vol $/j | marge/eq |
|---|---:|---:|---:|---:|---:|---:|---:|
| or | 20.5% | 1.62 | 8.3 | 31.7% | +4.4 | 260 | 3.2% |
| J1 | 51.3% | 4.04 | 16.3 | 24.7% | −8.6 | 236 | 4.0% |
| overnight | 26.4% | 2.08 | 13.8 | 43.3% | +8.5 | 304 | 4.2% |
| ORB | 1.8% | 0.14 | 0.14 | 0.4% | +0.3 | 26 | 0.3% |

vs budgets spec (or 0.5 / jpy 0.5 / on 0.6/jambe / ORB 0.25% taper) : le vol-targeting
sur-charge massivement J1 (jambe basse-vol → 16×eq actif) sans part de risque équivalente ;
l'overnight, budgété "0.6/jambe", est en réalité LE porteur de risque (43%). IS≈OOS (±3 pts).
Book : drift $4.6/j, vol $465/j (4.6%/j sur $10k). Identité comptable : exacte sur 2,244
tentatives (résidu max = le dip synthétique ORB 1.31R sur jours de bust, phantom de règle,
documenté).

**P1.2 cap de marge** : binds 5.3% des rebalances (8,939 snapshots) ; quand il mord :
need médian 69% → trim ×0.87 médian, proportionnel (toutes jambes au prorata, ORB exclu).
Jambes dominantes aux moments de binding : J1 + overnight (les deux grosses).

## P2 — Attribution (tables/p2_*.csv, plots/p2_waterfall.png, p2_loo_tornado.png)

**2.1 P&L par outcome (pooled, $/tentative)** : pass : or +340, J1 +265, overnight +405,
ORB +7 (total +1,017). bust_floor : or −524, J1 −333, overnight −621, ORB +1 (−1,477).
Cohortes FUNDED (n=393) : overnight +390, or +288, J1 +54, ORB +7. NOT-FUNDED (n=69) :
J1 **−1,932**, or −816, overnight −615, ORB +21. → l'overnight gagne les cohortes gagnées ;
J1 perd les cohortes perdues.

**2.2 LOO (paired, CI95 block, pooled ; baseline 84.6 / EV +$905)** :

| arm | Δp pts | CI95 | Δp IS | Δp OOS | ΔEV | Δmed_t |
|---|---:|---:|---:|---:|---:|---:|
| **overnight iso-vol** | **−10.6** | **[−20.6;−1.1]** | −17.6 | −3.5 | **−$186** | +1j |
| overnight no-resc | −10.4 | [−19.9;−1.3] | −14.2 | −6.6 | −$135 | +1j |
| or no-resc | −9.7 | [−17.7;−1.7] | −19.3 | 0.0 | −$151 | +1j |
| or iso-vol | −3.5 | [−10.8;+4.1] | −14.2 | **+7.4** | −$64 | +1j |
| J1 iso-vol | −5.2 | [−11.9;+1.7] | −9.0 | −1.3 | −$58 | +1j |
| J1 no-resc | −2.2 | [−9.1;+4.8] | −7.3 | +3.1 | **+$8** | +3j |
| ORB iso-vol | **+3.9** | [−1.5;+9.3] | +1.3 | +6.6 | **+$79** | 0j |
| ORB no-resc | +3.7 | [−1.7;+9.1] | −0.4 | +7.9 | +$74 | −1j |

→ **Ablation overnight (item 4 checklist) : verdict KEEP** — seul retrait dont le CI exclut
zéro, dans les deux variantes. Caveat maintenu : la preuve STANDALONE du sleeve reste faible
(DSR 0.29 vs sa grille de sélection, audit) ; ce verdict est in-container, pas une validation
du signal en soi. Or : era-asymétrique (IS porteur −19.3 ; OOS substituable +7.4 iso-vol).

**2.3 Flag-only (risque 1e-12, signal gardé)** : flag_gold ≡ loo_gold_noresc (74.9),
flag_jpy ≡ loo_jpy_noresc (82.5), flag_on ≡ loo_on_noresc (74.2), flag_orb 88.1 ≈ orb-removed
88.3. **Le rôle mécanique des 4 sleeves est nul une fois la micro-trade rule en place** — le
finding ORB de l'audit (day-counter) ne se généralise pas en mécanique résiduelle.

**2.4 Drift vs variance** : moteurs de drift = overnight (+8.5) + or (+4.4) ; J1 drift
NÉGATIF (−8.6, saignée de coûts : re-trade quotidien d'une jambe 16×eq à 0.57 bps/side) ;
variance = overnight 43 / or 32 / J1 25 / ORB 0.4. Le gap iso-vol-vs-no-rescale isole le
canal variance : or no-resc −9.7 → iso −3.5 (la variance d'or est re-fabricable par levier,
+6.2 pts récupérés) ; J1 −2.2 → −5.2 (sa variance est DIVERSIFIANTE : re-leverager
or/overnight la remplace MAL). Relation L-variance-vs-drift : le book passe par variance
(placebo container 62 pts) mais les +22.5 pts d'edge sont du DRIFT, porté par overnight+or.
Sweep vm 10-18 : p 82.5-84.6 (plateau confirmé, vm10 EV +$938 légèrement meilleur, ns).

**2.5 Busts (n=552 jours de breach)** : P&L moyen jour-de-breach : overnight −$338,
or −$276, J1 −$201, ORB 0. **Lundi = 31% des busts** : or −$419 + J1 −$175 (gap weekend —
seules jambes tenues, par construction) + overnight −$418 (jambes ON fraîches du lundi soir,
17:35/22:05) ; le « Monday bust » est moitié gap-weekend (or/J1), moitié premier-soir ON.

**2.6 Synthèse par sleeve** :
- **Overnight midweek — MOTEUR.** 26% du notionnel, 43% du risque, 2× le drift book ; seul
  retrait CI-significatif (−10.6 iso-vol). Gagne les cohortes gagnées (+$386/cohorte funded).
  Porte aussi les premiers-soirs de busts (−$418 les lundis de breach) : moteur ET premier
  fournisseur de variance — exactement ce que le container exige. KEEP (in-container).
- **Or trend — MOTEUR n°2 / variance remplaçable.** +$4.4/j, −9.7 pts si retiré sans
  re-levier ; MAIS iso-vol ns et OOS +7.4 (sa contribution OOS est substituable par levier).
  Era-dépendant (porteur surtout IS/2013-19). KEEP, sans illusion d'irremplaçabilité.
- **J1 — FOURNISSEUR DE VARIANCE DIVERSIFIANTE, drift négatif.** La plus grosse jambe (16×eq
  actif) pour 25% du risque et −$8.6/j de drift (coût de re-trading, pas le signal : SR
  standalone +0.42). Retrait ~gratuit (−2.2 ns, EV +$8, −0.42 essais) ; remplacement par
  levier pire (−5.2). Ni motor ni dead weight : amortisseur de forme. Candidat à
  re-dimensionnement (hors périmètre v2.1 — non testé au-delà du LOO pré-enregistré).
- **ORB — LEST (challenge) / moteur d'EXTRACTION (funded).** 1.8% du notionnel, 0.4% du
  risque, +$0.3/j ; son retrait AMÉLIORE p de +3.7/+3.9 pts et l'EV de +$74-79. Tout son rôle
  mécanique (day-count) est désormais porté par la micro-trade rule. Sa justification dans le
  BOOK est le funded uniquement (−52% d'extraction si mort — audit C40). Décision rationnelle :
  ORB OFF pendant le challenge, ON en funded — à inscrire comme variante v2.2 si adoptée
  (changement de spec, hors gel actuel).

## P3 — Start timing (tables/p3_buckets.csv, plots/p3_start_buckets.png)

Grille step-1 : n=3,223 cohortes (2013-10→2026-02), p inconditionnel **85.6%**, essais 3.28.
27 buckets pré-enregistrés, CIs block-bootstrap (blocs 65), N_eff/bucket affiché (19-237 —
**CIs larges, lire avec ça en tête**) :

- **H1 jour de semaine** : 84.6% (mer) → 86.6% (lun). |z| ≤ 0.39. Le mécanisme « lundi-bust »
  ne crée AUCUN avantage de jour de départ (les retries re-synchronisent le calendrier).
- **H2 FOMC-week** : 85.2 vs 85.7 (z −0.14). **CPI-week** (OOS-only 2020+, flaggé) : 83.2 vs
  82.9 (z −0.51). Néant.
- **H3 régime ORB trailing (3mo, seuils canoniques 0/0.08)** : unfav **90.6%** [84.5;95.9] /
  neutral 84.9 / fav **79.3** [70.1;86.9]. z_max = +1.70 — le plus gros signal de la grille,
  de sens ANTI-intuitif (cohérent : alternance mensuelle ORB documentée + ORB-nuisible au
  challenge). **Ne survit pas à la déflation** (1.70 < 2.57) → non actionnable, consigné.
- **H4 état or à t0** : flat 81.3 / long 88.7 / short 89.5 (z ≤ 1.19). Mécanisme plausible
  (book sans moteur or = plus de timeouts) mais sous le seuil.
- **H5 mois (descriptif)** : 80.5 (avr) → 90.4 (fév), z ≤ 0.86, N_eff 19-63 — bruit, aucune
  recommandation (pré-déclaré).

**Déflation** : 27 buckets, barre √(2 ln 27)=2.57 ; max |z|=1.70 → **AUCUNE fenêtre ne
survit**. EV : tous buckets +$810 à +$1,027 ; coût d'opportunité d'attendre la « meilleure »
fenêtre non-validée > son gain espéré (le funnel re-essaie de toute façon).

**→ Recommandation : start anytime.**

---
*Artefacts : tables/ (12 CSV), plots/ (4 PNG), baseline_day_records.parquet (13,068
jours-tentatives attribués, identité comptable exacte), attr_engine.py, run_*.py.
Conventions EV : VAL=$1,453/FEE=$96 (caveat audit C04 : $1,342 → −$95/campagne sur tous les
chiffres EV, ordres inchangés). Étude pré-enregistrée : aucun bucket/variante ajouté post-résultats.*
