# État réel des sleeves à poids zéro — XAUUSD (or) & USDJPY (J1)

**Date d'analyse : 2026-08-17** · Compte FUNDED $10k `<ACCOUNT_ID>` armé ce jour · Auteur : audit read-only (VPS lu, jamais écrit)
Notation : **[V]** vérifié (citation code / sortie de commande), **[D]** déduit d'un calcul explicité, **[NV]** non vérifiable ici, **[OP]** opinion macro.

---

## VERDICT (5 lignes)

1. **OR** — éteint depuis le **2026-04-15** (124 j cal. / **88 jours ouvrés**, le **3e plus long arrêt sur 172** depuis 2007). Cause : dead-zone θ=0.34 avec 3 lookbacks ⇒ **unanimité requise**, et les signes sont **(60j −, 120j −, 250j +)**. Rallumage **immédiat** exige spot **≥ 5 288** (+19.7 %) ou **≤ 3 536** (−20.0 %) : corridor mort de **39.6 % du spot**. Rallumage **par écoulement de fenêtre**, à spot inchangé : pas avant **~novembre 2026**. **Plausible à 3-6 mois (P≈47-67 %), pas imminent — et plus probablement en SHORT qu'en LONG.**
2. **J1** — poids zéro en production depuis le **2026-07-06** (déploiement de l'overlay) ; la **condition de gate est vraie depuis le 2026-03-27** (**143 j cal. / 101 j ouvrés**). USDJPY **159.23** ; il faut **10 clôtures consécutives ≤ 155** (−4.23 yen, −2.66 %, ≈ 5.9 σ quotidiens). **Improbable : P(gate ouvert) 6 % à 1 mois, 27 % à 3 mois — mais P(sleeve réellement vivante) 2.4-6.3 % seulement**, parce que la condition de réouverture **détruit mécaniquement** le signal momentum 12-1 long-only qu'elle est censée libérer.
3. **Le résultat le plus important n'est pas une probabilité, c'est un défaut de conception** : le gate J1 (160/155/10) a été ratifié sur un échantillon où la zone valait **17 jours en 13 ans (2.53 %)** ; en 2026 elle vaut **62.5 % des séances**. Le livre ne vit donc PAS l'arm ratifié (**GATE160, Δp +0.65 pt [0.00, +1.95]**) mais l'arm **FULLOFF**, que l'étude elle-même chiffre à **Δp −7.58 pt [−12.99, −2.81] / ΔEV −$87.6** — la borne pire-cas, subie depuis 101 séances sans qu'aucune décision ne l'ait actée.
4. **La chose à surveiller — J1** : PAS le niveau spot, mais le champ `audit.j1_gate.suspend` **ET** `audit.signals.j1_mom_12_1` dans `targets.json`. Les deux doivent être simultanément favorables ; historiquement ils s'excluent.
5. **La chose à surveiller — OR** : le franchissement du **120j**. À spot inchangé la référence 120j passe sous le spot vers le **2026-11-25** ; le premier état unanime du scénario déterministe tombe le **2026-11-02** et il est **négatif (short)**.

---

## 1. Tableau opérationnel

| | **XAUUSD (or)** | **USDJPY (J1)** |
|---|---|---|
| Poids live | **0.0000** [V] `targets.json` `ea_w_xauusd` | **0.0000** [V] `targets.json` `ea_w_usdjpy` |
| Zéro depuis (production) | **2026-04-15** (dernier signal non nul 2026-04-14, sig=+1.0) [V] | **2026-07-06** (dernier `w_jpy=+1.5000` le 2026-07-03) [V] `logs/ftmo_brain.log` |
| Zéro depuis (condition) | idem | **2026-03-27** (latch du gate) [V] |
| Durée | 124 j cal. / **88 j ouvrés** | 143 j cal. / **101 j ouvrés** |
| Variable qui gate | `sig` = moyenne des signes 60/120/250 sur prix carry-ajusté | `close(USDJPY)` (niveau ABSOLU) |
| Valeur courante | **sig = −0.3333** ; signes (60j **−5.16 %**, 120j **−17.74 %**, 250j **+23.00 %**) [V] | **159.2315** live / 159.505 (close panel 2026-08-13) [V] |
| Seuil | `\|sig\| ≥ 0.34` ⇒ **3/3 lookbacks du même signe** | `≤ 155.00` pendant **10 clôtures consécutives** (toute clôture > 155 remet le compteur à 0) |
| Écart au seuil | **0.0067 de sig** — mais indivisible : il faut faire **basculer un signe entier**. En prix : **+19.65 %** (long) ou **−19.98 %** (short) à références figées | **−4.2315 yen = −2.66 % = 5.9 σ quotidiens** (σ_1j = 0.447 %), **puis** tenir 10 séances |
| Chemin sans mouvement de prix | 60j bascule + le **2026-09-01** (k=13 j.o.), 120j le **2026-11-25** (k=74). Premier état unanime du scénario : **k=57 → 2026-11-02, en SHORT** | **aucun** — le gate est un niveau absolu, le temps ne le rouvre jamais |
| Verdict | **Plausible à 3-6 mois**, pas imminent | **Improbable ; à 12 mois quasi nul en tant que sleeve VIVANTE** |

### Formules exactes (citations)

**Or** — `data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py:135-142` :
```python
p = px["XAUUSD"].dropna()
tr = np.log(p).diff() + sL["XAUUSD"].reindex(p.index).fillna(0) / 1e4   # carry-ajusté (swap LONG)
base = np.exp(tr.cumsum())
sig = sum(np.sign(base / base.shift(L) - 1.0) for L in lookbacks) / len(lookbacks)   # L ∈ (60,120,250)
sig = sig.where(sig.abs() >= theta, 0.0)                                # theta = 0.34, signature l.125
```
Puis vol-target 10 %/60j (`:143-144`), book-vol 60j (`:148-149`), vol-derisk 20j (`:150-151`), equity-gate MA100 ×1.0/×0.4 (`:155-161`). **Aucune de ces couches ne peut produire 0** : seule la dead-zone le peut. [V]

**Point clé, non documenté correctement dans le repo** : avec **3** lookbacks, `sig ∈ {−1, −1/3, +1/3, +1}`. Comme **1/3 = 0.3333 < 0.34**, un accord **2 contre 1 est ZÉRO**. Le seuil impose donc l'**UNANIMITÉ**. Or `ftmo_live/DOC_SIGNAL_PIPELINE.md:37` écrit *« il faut ≥ 2 des 3 lookbacks d'accord »* — **faux**, et de nature à faire surestimer le duty cycle de la sleeve par tout opérateur futur. [V]

**J1** — `engine.py:164-168` :
```python
pj  = px["USDJPY"].dropna()
mom = pj.shift(21) / pj.shift(252) - 1.0        # momentum 12-1
sj  = (mom > 0).astype(float)                   # LONG-ONLY (jamais short, jamais négatif)
w_jpy = (sj * (0.10 / rvj).clip(upper=5.0)).shift(1).clip(-1.5, 1.5)
```
**mom actuel = +0.0986 > 0** ⇒ **le signal natif serait LONG au clip maximal (1.50)**. Le zéro vient **uniquement** de l'overlay. [V]

**Gate J1** — `ftmo_live/lib/j1_gate.py:27` et `ftmo_live/config/j1_gate.json` :
```python
DEFAULTS = dict(enabled=True, t_off=160.0, t_on=155.0, n_resume=10)
```
`_off_state` (`j1_gate.py:49-71`) : `state=False` au départ ; **latch à `close >= 160.0`** ; **reprise seulement après `n=10` clôtures consécutives `<= 155.0`** ; **une seule clôture > 155 remet `run_below` à 0**. Injection : `brain.py:163-165` → `weights["USDJPY"]=0.0` → `ea_w_usdjpy=0` → l'EA gelé aplatit J1 au rebalance 22:05 et ne rouvre pas. [V]

**Le CLAUDE.md est confirmé** : « USDJPY < 155 pendant 10 jours » est exact au code près (`<= 155.0`, clôtures **consécutives**, jours **ouvrés du panel**). [V]

### Preuve live (VPS, lecture seule)

`targets.json` (déposé 2026-08-17 15:00 Paris par `monday_restamp`, source 2026-08-14) : [V]
```
ea_w_xauusd = 0.0 ; ea_w_usdjpy = 0.0 ; ea_on_day = 1 ; ea_phase_hint = P2 (restamp J-3)
audit.signals   = {gold_last_close 4349.77 (2026-08-13), jpy_last_close 159.505, j1_mom_12_1 +0.0986}
audit.j1_gate   = {suspend: true, level: 159.505, t_off 160.0, t_on 155.0, n_resume 10, reason "in_zone", source "config"}
```
`state.json` (2026-08-17 16:50 Paris) : `XAUUSD 4419.295`, `USDJPY 159.2315`, `phase FUNDED`, `equity/balance 10000`, `positions []`, **`kill: 1`**, `last_error "kill-file FLAT — EA désarmé"`, `targets_status MISSING`. [V]
→ **Contexte à signaler** : au moment de l'audit le compte funded est **désarmé** (fichier `FLAT` déposé 2026-08-17 13:03 UTC), `flat_today=1`, `open_days=0`, `attempt_start 2026-08-17`. C'est cohérent avec une bascule P2→FUNDED en cours (archives `*.p2_archive_20260817` à 07:00) mais **ce n'est pas un état armé** ; à vérifier par l'opérateur. [V]
→ Également : `spec_bounds_breach = 1`. Le swap **long or live est −93.35 pts contre une ancre gelée à −65.68** (+42 % de coût de portage). [V]

---

## 2. Prix et structure de tendance (chiffres, pas d'adjectifs)

### XAUUSD

| Mesure | Valeur | Source |
|---|---|---|
| Spot live (broker FTMO) | **4 419.295** (2026-08-17 16:50 Paris) | `state.json` [V] |
| Spot marché (agrégat web) | ~4 386-4 406 (2026-08-17) | web, cf. §3 [V-source] |
| Dernière clôture panel | 4 349.77 (2026-08-13) | cache live [V] |
| Réf. 60j (2026-05-21) | 4 540.44 → **rendement carry-adj −5.16 %** | [V] |
| Réf. 120j (2026-02-25) | 5 170.69 → **−17.74 %** | [V] |
| Réf. 250j (2025-08-25) | 3 364.43 → **+23.00 %** | [V] |
| Plus haut de clôture (panel, 2000-2026) | **5 399.72 le 2026-01-28** | [V] |
| Distance au plus haut | **−19.4 %** (clôture) / **−18.2 %** (spot live) | [D] |
| Vol annualisée 60j / 250j | **25.5 % / 27.9 %** | [V] |
| Portage inclus dans le signal | **−1.99 bps/jour** (moyenne 250j du panel) ≈ **−5.0 %/an** ; live **−2.11 bps/nuit** ≈ **−5.3 %/an** | [V]/[D] |

**Ce que ça veut dire mécaniquement.** L'or a fait un sommet fin janvier 2026, perdu ~20 %, et se stabilise. Le signal voit donc une **hausse longue (250j) posée sur une baisse moyenne (120j et 60j)** — la configuration exacte que la dead-zone d'unanimité neutralise. Les deux issues de sortie sont symétriques et lointaines :
- **LONG** : il faut annuler la baisse 120j ⇒ spot **≥ 5 287.90** aujourd'hui (**+19.65 %**), le 60j (4 586.28, +3.78 %) étant le seuil facile mais insuffisant à lui seul.
- **SHORT** : il faut annuler la hausse 250j ⇒ spot **≤ 3 536.38** (**−19.98 %**).
- Le corridor mort fait **1 751.5 points = 39.6 % du spot**. [D]

**Effet du temps (le vrai canal).** Les références roulent. À spot rigoureusement inchangé (portage inclus), la trajectoire des signes simulée jour par jour est : `(−,−,+)` aujourd'hui → `(+,−,+)` au **2026-09-01** → oscillations → **premier état unanime `(−,−,−)` le 2026-11-02** (k=57 j.o.), puis le 120j bascule positif vers le **2026-11-25**. [D — scénario déterministe, fragile : plusieurs de ces bascules se jouent à moins de 1 % de prix]

### USDJPY

| Mesure | Valeur | Source |
|---|---|---|
| Spot live | **159.2315** (2026-08-17 16:50 Paris) | `state.json` [V] |
| Clôture panel | 159.505 (2026-08-13) | [V] |
| Momentum 12-1 (le signal) | **+9.86 %** (p[t−21]=161.9-ish / p[t−252]=147.345 du 2025-08-26) | [V] |
| Min / max 250 j.o. | **146.44 / 163.856** | [V] |
| Min / max 2026 | 152.282 (2026-01-27) / 163.856 | [V] |
| Dernière clôture ≤ 155 | **2026-02-23 à 154.605** | [V] |
| Nb de clôtures ≤ 155 en 2026 | **15 sur 160** (toutes en janvier-février) | [V] |
| Vol annualisée 60j / 250j | **7.10 % / 7.98 %** ; σ quotidien 60j = **0.447 %** | [V] |
| Séquence récente | 2026-07-29 **163.452** → 07-30 **159.584** (−3.87 yen en une séance) → 08-13 **159.505** | [V] |

Le saut du 30 juillet dans le panel correspond exactement à l'intervention rapportée (§3). **La paire a rendu la moitié du mouvement en deux semaines** : 157.19 (08-03) → 159.51 (08-13). [V]

---

## 3. Macro — daté, sourcé, et étiqueté

> Tout ce qui suit est du **contexte sourcé** ; les jugements directionnels sont marqués **[OP]** et n'entrent dans aucun chiffre du §4.

### Or

- **Fed** : le FOMC a maintenu les Fed funds à **3.50-3.75 %** le **29 juillet 2026**, cinquième réunion consécutive de statu quo, par **9-3** — les trois dissidents (Hammack, Kashkari, Logan) demandant des taux **plus hauts**, l'inflation dépassant 2 % depuis plus de cinq ans. [V-source : Fed, CNBC 2026-07-29]
- **Marché de taux** : au **17 août 2026**, des ventes au détail de juillet à **−0.6 %**, une inflation plus tiède et une confiance en baisse ont ramené la probabilité d'une **hausse** en septembre à **~30 %**. [V-source : synthèse presse 2026-08-17]
- **Prix** : record de janvier 2026 (≈ **5 598** selon les sources presse, **5 399.72 en clôture** dans le panel broker), puis **plus de 20 % de baisse** — le pire trimestre depuis 2013 — puis un rebond vers 4 500 le 11 août. Au 17 août : **~4 386-4 406** spot, **4 419.295** sur le flux FTMO. [V-source, avec une réserve : une source datée du même mois donne « ~4 020 », **incohérente avec quatre autres et avec le flux broker** → écartée]
- **Banques centrales** : **244 tonnes nettes achetées au T1 2026** ; **45 %** (record) des banques centrales interrogées par le WGC prévoient d'ajouter. [V-source : WGC]
- **Prévisions vendeurs** : J.P. Morgan vise 6 000 $/oz fin 2026 et évoque 6 300 $ en 2027 ; SSGA discute un scénario 5 000 $. **[OP tierce — ce sont des opinions de sell-side, à ne pas confondre avec une mesure. Aucune n'entre dans le §4.]**

**Lecture pour la sleeve [OP]** : la configuration de taux réels est ambiguë (Fed en pause avec un biais dissident **haussier**, ce qui est un vent contraire pour l'or, contre une demande officielle structurellement acheteuse). Ce qui est **mesuré**, en revanche, c'est que la sleeve ne demande pas une opinion : elle demande **+19.7 % ou −20.0 %**, ou **trois mois d'écoulement de fenêtre**.

### USDJPY

- **BoJ** : taux directeur à **1.00 %** (monté en **juin 2026**), maintenu le **31 juillet 2026** par **8-1**, avec relèvement des perspectives économiques et avertissement d'un possible dépassement de la cible d'inflation. [V-source : FXStreet 2026-08-05]
- **Politique** : le gouvernement Takaichi soutient une hausse **rapprochée**, le marché voyant le prochain mouvement en **septembre ou octobre 2026**. [V-source : Bloomberg 2026-08-13]
- **Différentiel** : **1.00 %** (Japon) contre **3.50-3.75 %** (Fed) — soit **2.50-2.75 points**. Le spread souverain 30 ans US-Japon s'est réélargi à **2.83 %** fin juillet. [V-source : OMFIF 2026-08-07 ; FXStreet]
- **Interventions du MoF — historique 2026 mesuré, pas supposé** :
  - **30 avril 2026** : USDJPY touche **160.70** ; la ministre Katayama et le vice-ministre **Mimura** émettent un *« final evacuation warning »*, la paire rebondit vers 159. [V-source]
  - **26 avril → 29 mai 2026** : intervention confirmée par le MoF, **9 788,5 milliards de yen (≈ 62,25 Md$)**. [V-source]
  - **30 juillet 2026** : intervention conjointe **Japon + US Treasury**, USDJPY passe de **~163-164 à ~155-157** en séance ; estimations **~75 Md$ côté japonais, 5-10 Md$ côté américain**, financé via la facilité **FIMA** de la Fed. Bessent : un yen faible « tirerait vers le bas les autres devises asiatiques ». [V-source : OMFIF 2026-08-07 ; note Miyano]
  - **14 août 2026** : la paire est **revenue à 159.30-159.43**, ayant rendu **~la moitié** du gain de l'intervention, et signe sa pire semaine en trois mois. [V-source]
- **Niveaux d'intervention historiques** : la ligne défendue en avril 2024 était **160** ; c'est explicitement la justification du `t_off` du gate (§5). En 2026 le marché a coté jusqu'à **163.856 en clôture** — **au-dessus** de toute borne du modèle d'origine (max 161.57 à la conception). [V]

**Lecture pour la sleeve [OP]** : deux interventions massives en quatre mois n'ont pas ramené la paire sous 158, et le portage reste payé par un différentiel de 2.5-2.75 pts. Pour atteindre **10 clôtures consécutives ≤ 155** il faut soit un resserrement BoJ effectif et répété, soit un virage Fed accommodant, soit une troisième intervention **suivie d'un maintien** — ce que ni avril-mai ni juillet n'ont produit. **C'est une opinion ; le chiffre défendable est au §4.**

---

## 4. Probabilité de rallumage — et sur quoi elle repose

**Méthode [D]** : block bootstrap (blocs de 10 séances, tirage circulaire) sur les rendements log quotidiens des **5 dernières années** du panel, appliqué au niveau live, puis application **de la règle de gate exacte** (même code que la production) sur chaque trajectoire simulée. Deux jeux : **dérive nulle** (rendements dé-moyennés — la base honnête) et **dérive historique** (rapportée pour l'encadrement). 4 000 à 20 000 tirages. **Aucune opinion macro n'entre dans ces nombres.**

### Or — P(sleeve non nulle à l'horizon)

| Horizon | Dérive nulle | dont LONG | dont SHORT | Dérive historique (+13 %/an) |
|---|---:|---:|---:|---:|
| 1 mois | **26.7 %** | 24.7 % | 2.0 % | 34.5 % |
| 3 mois | **66.9 %** | 29.2 % | 37.7 % | 66.7 % |
| 6 mois | **46.2 %** | 7.7 % | 38.5 % | 40.2 % |
| 12 mois | **57.6 %** | 28.0 % | 29.5 % | — |

Ancrage historique indépendant : la sleeve a été **active 56.1 % des séances 2007-2026** (4 825 obs), **44.0 % en 2026**, contre **79.9 % en 2024** et **84.5 % en 2025**. L'arrêt en cours (**88 j.o.**) est le **3e plus long sur 172 arrêts** (médiane **4 j.o.**, p90 **36 j.o.**, record 131 j.o. en 2018-2019). **98.3 % des arrêts historiques étaient plus courts.** [V]

**Ce que ces chiffres disent et ne disent pas.** La non-monotonie (67 % à 3 mois, 46 % à 6 mois) n'est pas une erreur : c'est la signature d'un signal qui **oscille** entre `±1/3` et `±1` au fil du roulement des fenêtres. **P(actif à l'horizon exact)** est la bonne mesure pour une décision d'allocation ; **P(actif au moins un jour)** — 94 % à 3 mois — est trompeuse opérationnellement (elle compte des allumages d'un ou deux jours, c'est-à-dire du whipsaw payé au spread). Je rapporte la première.
**À souligner** : à 6 mois, le rallumage est **5× plus probable en SHORT qu'en LONG** (38.5 % vs 7.7 %). Le portage négatif inclus dans le signal (−5.0 à −5.3 %/an, aggravé de 42 % vs l'ancre gelée) **pousse structurellement le blend vers le short**. Une jambe or **short** n'a jamais été discutée dans les études de book consultées ; elle est pourtant l'issue modale. [D]

### J1 — deux probabilités, et seule la seconde compte

| Horizon | P(gate OUVERT) | P(mom 12-1 > 0) | **P(sleeve VIVANTE)** |
|---|---:|---:|---:|
| 1 mois | 6.3 % | 100 % | **6.3 %** |
| 3 mois | 26.5 % | 65.0 % | **2.4 %** |
| 6 mois | 36.4 % | 68.4 % | **6.3 %** |
| 12 mois | 42.0 % | 49.8 % | **0.4 %** |

*(dérive nulle ; avec la dérive historique de la paire, +7 %/an : 3 mois 1.6 %, 6 mois 4.6 %, 12 mois 0.2 %)*

**Le produit n'est pas le produit des marges — les deux événements sont anti-corrélés par construction**, et c'est démontrable sans simulation :
- Rouvrir le gate exige **10 clôtures consécutives ≤ 155**.
- Le signal exige `p[t−21] > p[t−252]`.
- Passé 21 séances après la réouverture, `p[t−21]` est **nécessairement ≤ 155** ⇒ le signal n'est long que si USDJPY valait **moins de 155 un an plus tôt**.
- Vérification directe sur les données réelles : si la paire est à **155 dans 63 séances**, alors `p[t−252] = 156.378` ⇒ **mom = −0.88 % ⇒ sleeve à zéro**. À **126 séances**, `p[t−252] = 154.958` ⇒ **mom = +0.03 %**, sur le fil. À **150**, mom = **−4.08 % / −3.20 %** ⇒ zéro. [V]

**Conclusion honnête** : la seule fenêtre où J1 peut réellement porter du risque est **les ~3 à 4 semaines qui suivent immédiatement une réouverture**, avant que `p[t−21]` ne bascule sous 155. Passé ce délai la sleeve s'auto-éteint. Toute planification qui traite J1 comme un diversifieur « en attente de 155 » **surestime le mécanisme**.

**Ce que je ne peux pas estimer** : la probabilité conditionnelle à une hausse BoJ en septembre-octobre. Le bootstrap ne modélise pas les sauts d'intervention (le 30 juillet, −3.87 yen en une séance, est un événement que le bloc de 10 jours reproduit mal). **Direction du biais : P(gate ouvert) est probablement SOUS-estimée à court terme** (les sauts existent), et **P(sleeve vivante) reste bornée par l'argument mécanique ci-dessus, qui, lui, ne dépend d'aucun modèle.**

---

## 5. Le point de conception — un gate à niveau absolu, et ce qu'il a réellement coûté

### 5.1 Le seuil J1 n'est pas invariant au régime, et l'échantillon de conception est déjà périmé

**Justification documentée [V]** — `data/ftmo_portfolio/j1_suspend_study/PREREGISTRATION.md` :
> « **T_off = 160.00**, **T_on = 155.00**, **N = 10**. Justification (prospectif) : 160 = ligne BoJ effectivement défendue (avril-2024), plus sûre que 161.95 […] ; mord dans l'échantillon (17 j) donc coût mesurable. »

Et, dans la même pré-registration :
> « Jours ≥ seuil (2013-10→2026-06) : **≥161.95 : 0 ; ≥160 : 17** (tous 2024-06-26→2026-06-05) ».

Donc : **le seuil a une justification économique explicite (la ligne défendue d'avril 2024) et n'est PAS calé par optimisation** — c'est à porter au crédit de l'étude, qui déclare aussi son propre aveuglement (« le flash d'intervention 2026 est **hors-modèle** ; le backtest ne peut que **dégager le coût**, il ne **prouve pas le bénéfice** »). [V]

**Mais le régime a changé après la conception, et personne n'a re-évalué.** Fraction de séances où le gate aurait été OFF, calculée sur la série complète du moteur (5 104 obs, 2007-01→2026-08) : [V]

| Période | Fraction OFF |
|---|---:|
| **2007 → 2023 (17 années pleines)** | **0.0 % — exactement zéro, chaque année** |
| 2024 | 11.2 % (un seul épisode, 2024-06-26 → 2024-08-06) |
| 2025 | 0.0 % |
| **2026 (au 08-13)** | **62.5 %** |
| **Plein échantillon** | **2.53 %** |

Le gate a été conçu contre un événement de queue valant **2.5 % du temps sur 19 ans**. Il est aujourd'hui **le régime dominant** : latché sans interruption depuis le **2026-03-27**, soit **101 séances**, avec un maximum de clôture à **163.856** — **au-dessus du 161.57 qui était le maximum connu à la conception**. La réponse à la question posée est donc : **oui, c'est bien ce cas de figure.** Un seuil absolu sur une paire en dérive structurelle haussière ne se rouvre pas tout seul ; le temps travaille contre lui, pas pour lui.

### 5.2 Le coût réellement subi n'est pas celui qui a été ratifié

L'étude a mesuré **deux** bras et n'en a ratifié qu'un [V] (`STUDY.md`, 462 cohortes, EQUIV PASS 87.01, bootstrap bloc apparié 3 000 tirages seed 23) :

| Arm | p_pooled | Δp [CI90] | ΔEV [CI90] | Statut |
|---|---:|---|---|---|
| baseline (J1 plein) | 87.01 | — | — | — |
| **GATE160** (ce qui a été ratifié) | 87.66 | **+0.65** [0.00, +1.95] | **+$12.6** [$0.0, +35.2] | déployé |
| **FULLOFF** (J1 éteint partout) | 79.44 | **−7.58** [−12.99, −2.81] | **−$87.6** [−171.5, −11.4] | « borne pire-cas », **non retenue** |

Le **+0.65 pt** est un chiffre de régime rare : il provient de **3 cohortes exactement** (démarrages 2024-05-23, 06-03, 06-12), toutes basculées échec→réussite, sur 19 cohortes touchées. L'étude le dit elle-même : *« traiter comme ≈ gratuit, pas comme un edge »*. [V]

**Le point** : depuis le 2026-03-27, le gate n'est plus « ciblé », il est **permanent**. Le livre déployé est donc, en pratique, l'arm **FULLOFF** — celui que la pré-registration décrivait comme la **borne haute du coût** et qui vaut **−7.58 pt de p(pass) et −$87.6 d'EV**. Cette bascule d'arm ne résulte d'aucune décision : elle résulte du fait qu'un seuil absolu a été dépassé par le marché. Aucun mécanisme du système ne la signale, parce que le gate se comporte exactement comme spécifié. **C'est le mode de défaillance : la sleeve est morte de facto, dans les règles, sans qu'un humain l'ait décidé ni ne soit alerté.**

### 5.3 Et le gate est en conflit avec le signal qu'il protège

Développé au §4 : la condition de réouverture (10 clôtures ≤ 155) **produit** l'état qui met le momentum 12-1 long-only à zéro. Ce n'était pas testable au moment de la conception (le gate n'avait jamais eu à se rouvrir dans l'échantillon : **zéro réouverture entre 2007 et 2023**, une seule en 2024). **P(sleeve vivante) mesurée : 2.4 % à 3 mois, 0.4 % à 12 mois.** Un overlay de risque dont le coût est chiffré à « ≈ 0 » sur un échantillon où il ne mord jamais, et dont la porte de sortie annule le signal, n'est pas un overlay ciblé : c'est une **ablation à retardement**.

### 5.4 Or : problème différent, tout aussi structurel

Le gate or, lui, **est relatif** (retours glissants), donc il se rouvre : médiane des arrêts **4 séances**. Le problème n'est pas qu'il ne rouvre jamais, c'est son **duty cycle** et sa **provenance** :

- **θ = 0.34 est hérité, pas dérivé pour cette sleeve.** `REPORT.md:48` classe la spec or comme « archive-validée, **non re-minée** ». La source est `PropFirms/ftmo/program_2026-06/ftmo_research/tsmom/STRATEGY_DOSSIER_TSMOM.md:113` : `signal_i = 0 if |signal_i| < 0.34  # trend-strength filter`, dans une spec de **panier à 6 instruments** (US500, GLD, SLV, USO, BTC, ETH). Dans un panier, zéroer un instrument en laisse **cinq** ; le filtre coûte de la breadth, pas de l'exposition. **Porté verbatim sur une sleeve MONO-instrument, le même filtre devient un interrupteur marche/arrêt du book entier.** [V]
- **Conséquence chiffrée** : la sleeve décrite comme « le moteur du book » (`CHECKUP_2026-07-20.md:22`) est **absente 43.9 % des séances par construction**, et jusqu'à **85.6 % en 2017**. Aucun document consulté ne rapporte ce duty cycle.
- **Aucune justification du 0.34 en tant que valeur** n'a été trouvée dans le repo — ni dérivation, ni balayage, ni contre-test. **[NV]** : je ne peux pas dire s'il a été optimisé sur un échantillon ou simplement écrit. Ce que je peux dire, c'est que sa position — **juste au-dessus de 1/3** — a un effet qualitatif énorme (unanimité vs majorité) pour un écart de **0.0067**, et que **le repo se documente lui-même à tort sur cet effet** (`DOC_SIGNAL_PIPELINE.md:37`). Une valeur de 0.33 au lieu de 0.34 transformerait la sleeve en un objet **complètement différent**, et rallumerait le poids or **aujourd'hui, en short**.
- **Le portage est un biais directionnel non neutre** : le signal tourne sur un prix carry-ajusté au swap **LONG** (`engine.py:137`), soit −1.99 bps/j mesuré (−2.11 bps/nuit au tarif live actuel, **+42 % vs l'ancre gelée**, `spec_bounds_breach=1`). Cela **incline mécaniquement le blend vers le short** — d'où les 38.5 % de rallumage short contre 7.7 % de long à 6 mois. Le tarif de financement du broker déplace donc le **signal**, pas seulement le P&L.

### 5.5 Ce que je ne recommande pas

Je n'ai **pas** de correctif à proposer ici et je le dis explicitement : toucher au gate J1 ou à θ rouvre une pré-registration gelée, consomme le budget de 3 modifications, et — pour le gate J1 — retirerait une protection dont le motif (**deux comptes tués en 48 h par un flash d'intervention sur une position J1 à ~16.8×**, `STUDY.md §4`) est **toujours d'actualité**, comme le prouvent les interventions d'avril-mai et du 30 juillet 2026. **Le constat utile est le diagnostic, pas l'action** : l'opérateur doit savoir qu'il exploite un livre mono-moteur en connaissance de cause, et non attendre deux diversifieurs qui ne reviennent pas.

---

## 6. Limites

- **Données non re-téléchargées** : tous les prix historiques viennent du cache live du brain (`ftmo_live/runtime/cache_live/2026-08-14/panel_px.parquet`), lu en read-only sur le VPS. Ce panel est **gelé au 2026-06-05** puis **étendu de 49 barres** par l'export D1 de l'EA ; les seams rapportés dans `targets.json` sont **XAUUSD 7.04 bps, USDJPY 5.63 bps** (US100 30.5 et GER40 96.7 sont marqués `seam_warn`). Immatériel devant des écarts de 20 %, **matériel** devant les bascules de signe du scénario déterministe du §2, dont certaines se jouent à <1 % ⇒ **les dates de novembre 2026 sont indicatives, pas des engagements**. [V]
- **Fuseau du panel non revérifié au tick** : l'`AUDIT.md` du gate déclare une convention **EET/MT5** et considère l'écart immatériel à ~1 pip de 160.00. Je n'ai pas re-tick-matché (leçon L52 non ré-appliquée ici). **[NV]**
- **Le moteur n'a pas été ré-exécuté de bout en bout** : j'ai recalculé le blend or et le momentum J1 **avec la formule et le cache de production**, et les résultats concordent avec les sorties du brain (`w_xau=0`, `w_jpy=0`, `j1_mom_12_1=+0.0986`, `j1_gate.suspend=true`). Je n'ai pas re-couru `build_signals()` ni le gouverneur. **[D]**
- **Le bootstrap ne modélise pas les sauts d'intervention** ni la persistance des régimes : les blocs de 10 séances lissent un −3.87 yen en une séance. Biais déclaré au §4.
- **Un seul jour de prix live** : `state.json` donne un instantané (2026-08-17 16:50 Paris). Je n'ai pas de série intraday indépendante pour la journée du 17.
- **Le compte funded est désarmé au moment de l'audit** (`kill=1`, fichier `FLAT`, `targets_status MISSING`). Je n'ai pas cherché à savoir si c'est intentionnel — **à confirmer par l'opérateur avant toute lecture de ce rapport comme décrivant un livre en production active.** [V]
- **Non vérifié** : la valeur de θ=0.34 comme choix (optimisé ? repris d'un papier ?) ; l'existence d'un back-test de la sleeve or **short** ; l'impact du swap or à +42 % sur les métriques de book (aucune étude consultée ne l'intègre).
- **Pour aller plus loin, il faudrait** : (a) re-tick-matcher `panel_px` USDJPY contre `data/deep_history_utc/` pour certifier la convention horaire des clôtures qui arment le latch ; (b) re-courir le harnais 462 cohortes avec le gate **latché en permanence depuis 2026-03-27** pour chiffrer le coût réel (et non la borne FULLOFF, qui suppose J1 off sur **tout** l'historique) ; (c) mesurer le duty cycle de la sleeve or dans les études qui la nomment « moteur du book ».

---

## Sources web (datées)

- [Fed — FOMC statement, 29 juillet 2026](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm)
- [CNBC — Divided Fed holds rates steady, 29 juillet 2026](https://www.cnbc.com/2026/07/29/fed-rate-decision-july-2026.html)
- [FXStreet — USD/JPY August outlook (BoJ 1.00 %, vote 8-1 du 31 juillet), 5 août 2026](https://www.fxstreet.com/analysis/usd-jpy-august-outlook-diverging-central-bank-policies-keep-yen-under-pressure-202608050603)
- [Bloomberg — Japan's government supports faster BOJ rate hike, 13 août 2026](https://www.bloomberg.com/news/articles/2026-08-13/japan-s-government-is-said-to-support-faster-boj-rate-hike)
- [OMFIF — Japan's yen intervention and the US's unusual support, 7 août 2026](https://www.omfif.org/2026/08/japans-yen-intervention-and-the-us-unusual-support/)
- [Bloomberg — Japan's FX chief warns of 'bold' action after yen tops 160, 30 mars 2026](https://www.bloomberg.com/news/articles/2026-03-30/japan-s-fx-chief-warns-of-bold-action-after-yen-tops-160)
- [BigGo Finance — Mimura « final evacuation warning », yen au-delà de 160](https://finance.biggo.com/news/mQKi3p0BmHHDnbgyfkCF)
- [Univest — USD/JPY 14 août 2026, plus forte perte hebdomadaire en trois mois](https://univest.in/blogs/usd-jpy-today-yen-weekly-loss-august-14-2026-intervention)
- [World Gold Council — Gold Outlook 2026](https://www.gold.org/goldhub/research/gold-outlook-2026)
- [J.P. Morgan Global Research — Gold price predictions 2026-2027](https://www.jpmorgan.com/insights/global-research/commodities/gold-prices)
- [Investing.com — XAU/USD (niveau spot 2026-08-17)](https://www.investing.com/currencies/xau-usd)
- [LiteFinance — Gold price forecast (niveau spot 2026-08-17)](https://www.litefinance.org/blog/analysts-opinions/gold-price-prediction-forecast/daily-and-weekly/)

## Sources repo & VPS (citations vérifiées)

- `data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py:125,135-142,164-168` — signaux or et J1
- `ftmo_live/lib/j1_gate.py:27,49-71,74-95` · `ftmo_live/config/j1_gate.json` — gate 160/155/10
- `ftmo_live/brain.py:156-168` — injection du gate dans les poids
- `ftmo_live/DOC_SIGNAL_PIPELINE.md:37` — **description erronée du seuil** (« ≥2 des 3 » vs unanimité réelle)
- `data/ftmo_portfolio/v22/spec_v22.yaml:57` · `ftmo_live/mt5/spec_v22.mqh:82-85` — spec gelée
- `data/ftmo_portfolio/j1_suspend_study/{PREREGISTRATION,STUDY,AUDIT,MECANISME_SUSPENSION}.md` — conception, résultats, audit
- `PropFirms/ftmo/program_2026-06/ftmo_research/tsmom/STRATEGY_DOSSIER_TSMOM.md:113` — origine de θ=0.34 (panier 6 instruments)
- `data/ftmo_portfolio/REPORT.md:48` — « archive-validée, non re-minée »
- VPS (lecture seule) : `MQL5/Files/{targets.json, state.json, ea_state.json}`, `logs/{ftmo_brain.log, ftmo_monday_restamp.log}`, `ftmo_live/runtime/cache_live/2026-08-14/panel_*.parquet`
