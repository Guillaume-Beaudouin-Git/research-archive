# Vérification falsifiante — book trend J1+G1

**2026-06-03. Session falsifiante indépendante.** Vérifie le rapport
`data/ftmo_research/RAPPORT_replication_trend.md` + script `trend_replication.py`.

> **Cadre.** FTMO est déjà clos (cf `_FTMO_ETAT_CANONIQUE.md`). On ne re-prouve PAS
> FTMO. La seule question posée : le book J1+G1 (SR ~0,70 reporté) est-il un actif
> déployable (personal book / CV), ou un artefact de pipeline ?

---

## 0. Synthèse honnête (1 paragraphe)

Le book J1+G1 du rapport **se reproduit à l'identique** sous une twin littérale du
script. Sous une réécriture **indépendante** avec des choix d'implémentation
"raisonnables" mais différents (log-returns au lieu de simple returns, lag carry t-1
au lieu de t-2), le SR du book tombe à **0,47** au lieu de 0,70 — l'edge est
**fragile aux conventions d'implémentation à hauteur de ~0,15 SR**. Le filtre
"carry-aligned" de J1 est **cosmétique à 99,9 %** (carry US-JP > 0 sur 6849/6857
jours) : J1 est en pratique un **TSMOM long-only sur USDJPY**, dont **~70 % de la
variance** est expliquée par un simple buy & hold vol-targeté du carry-trade JPY
classique (β=0,51, R²=0,51). Le swap modélisé apporte **+0,175 SR à J1** (= 30 % du
SR) et n'a jamais été mesuré sur broker réel. Le skew daily −0,36 est confirmé et
stable structurellement, mais le skew **mensuel** est **positif** (+0,31), donc le
problème est spécifique à la barrière FTMO daily 5 %, pas à un personal book. **Pas
de leak résiduel détecté.** L'apport portefeuille du book à A+B existant est
**dilutif** (SR_port 2,31 vs 2,35 sans le book) — le SR du book (~0,62-0,71) est
trop faible pour qualifier comme strategy D (gate 2,59 ; atteint 2,31). Verdict : ce
n'est pas un artefact, mais ce n'est pas non plus un actif portefeuille — c'est un
**item CV** (réplication propre + 2 bugs attrapés + décomposition honnête) et un
**sleeve de secours** si A est gelé et B retardé.

---

## 1. Tableau des gates

| Gate | Question | Statut | Chiffre clé | Lecture |
|---|---|---|---|---|
| **G0** | Twin littéral reproduit-il J1/G1/book ? | ✅ PASS | J1=0,578 G1=0,664 book=0,698 (vs cible 0,58/0,66/0,70) | Pas un artefact de pipeline |
| **G0 bis** | Réplication indépendante (log-ret, lag t-1) | ⚠ PARTIEL | J1=0,45 G1=0,48 book=0,47 | Edge fragile aux conventions d'impl à ~0,15 SR |
| **G1** | Filtre carry-aligned est-il réel ? | ❌ KILL | carry<0 sur 0,1 % de la période (8/6857 j) ; J1 ≡ TSMOM long-only à 0,003 SR près | **Filtre cosmétique. J1 = TSMOM LO USDJPY, 70 % beta carry-trade.** |
| **G1 bis** | Alpha vs buy & hold USDJPY vol-targeté + swap | ⚠ MARGINAL | α = +2,11 %/yr, t=1,98 naïve | Alpha de timing TSMOM modeste, juste à la limite de significance naïve |
| **G2** | SR robuste à ±50 % sur swap modélisé ? | ⚠ FLAG | range book [0,49 ; 0,80], baseline 0,71, réaliste ~0,62 | Δ swap J1 = +0,175 SR (30 % du SR vient du carry encaissé) |
| **G3** | Skew tail honnête ? | ⚠ FLAG conditionnel | daily −0,36, mensuel **+0,31**, worst day −6,3 %, CVaR1 −3,4 % | Problème daily uniquement (barrière FTMO). Mensuel = sain |
| **G3 bis** | Pertes concentrées sur 2008/2020/2022 ? | ❌ MYTHE | 0/10 worst days dans ces années | "Carry-crash structurel" du rapport n'est pas observé |
| **G4** | Leak résiduel délai+1 ? | ✅ PASS | Δ SR(+1) = −0,12 / −0,19 / −0,22 sur J1/G1/book | Pas de leak |
| **G5** | Apport vs A (SR 1,33) et B (SR 2,0) ? | ❌ DILUTIF | corr book/A ≈ 0 mais SR_port(A+B+book) = 2,31 < SR(A+B) = 2,36 | Trop faible SR pour qualifier comme strategy D (gate 2,59) |

**Synthèse :** **G0 PASS conditionnel + G1 KILL (sur la prétention "carry-aligned trend")
+ G2 FLAG + G3 FLAG-FTMO-only + G4 PASS + G5 DILUTIF.** L'edge existe mais n'est pas ce
que le rapport dit qu'il est.

---

## 2. Verdict G1 — J1 carry-aligned ≡ TSMOM long-only USDJPY (le pivot)

### Le filtre carry est cosmétique à 99,9 %

| Statistique | Valeur |
|---|---|
| Jours total (USDJPY 2000-2026) | 6857 |
| Jours où signe(carry) actif = +1 (US > BoJ) | 6847 (99,9 %) |
| Jours où signe(carry) actif = −1 (US < BoJ) | **8 (0,1 %)** |
| Jours flat | 2 |
| Jours où filtre carry filtre EFFECTIVEMENT le mom | 3350 (= jours mom<0) |
| Jours signal J1 = +1 (long) | 3499 (51 %) |
| Jours signal J1 = 0 (cash) | 3351 (49 %) |
| Jours signal J1 = −1 (short) | **7 (0,1 %)** |

Le filtre "carry-aligned" n'écarte que les mom<0 et autorise les mom>0 (parce que
carry>0 ≈ tout le temps). **C'est arithmétiquement équivalent à
`signal = max(mom, 0)`**, soit un TSMOM long-only.

**Preuve numérique** :

| Sleeve | Sharpe | skew | MDD (vol 10 %) |
|---|---|---|---|
| J1 carry-aligned (rapport) | **+0,578** | −0,29 | −27,9 % |
| TSMOM long-only (sans mention de carry) | **+0,581** | −0,29 | −28,0 % |
| Δ | 0,003 | 0,00 | 0,1 % |

Les deux séries sont **indiscernables**. Le carry-filter n'a aucun effet causal
sur la performance — il est arithmétiquement neutre quand carry > 0 toujours.

### J1 ≡ 70 % beta carry-trade + 30 % timing TSMOM

OLS J1 = α + β × buy_and_hold_USDJPY_voltargeté + ε (sur fenêtre commune) :

| Stat | Valeur | Lecture |
|---|---|---|
| β | **+0,508** | J1 a une exposition systématique 0,5× au carry-trade JPY |
| α daily | +0,837 bps/j ≈ **+2,11 %/yr** | Timing TSMOM ajoute un alpha modeste |
| t-stat α (naïve, non HAC) | **+1,98** | Juste à la limite de significance ; en HAC lag-6 probablement < 2 |
| R² (J1 ~ BH) | **0,507** | La moitié de la variance J1 est expliquée par le beta carry-trade |
| corr J1 vs BH | +0,712 | Très corrélé |
| SR J1 | 0,578 | |
| SR buy & hold + swap | 0,437 | |
| SR buy & hold SANS swap | 0,232 | → swap apporte 0,20 SR au BH passif lui-même |
| **Décomposition** | β × SR_BH ≈ 0,22 + α_timing ≈ 0,36 → 0,58 | Beta apporte ~38 %, timing TSMOM apporte ~62 % du SR (en termes daily) |

**Interprétation :** J1 fait deux choses combinées :
1. **Encaisse un beta passif sur le carry-trade JPY** (long USDJPY quand US>JP),
   qui à lui seul produit SR 0,44 (dont 0,20 vient du swap encaissé modélisé).
2. **Met en cash pendant les downtrends USDJPY** (filtre TSMOM long-only). Ce
   timing évite les drawdowns du buy & hold passif (MDD 37 % → 28 %), et ajoute
   ~0,14 SR au SR du buy & hold (0,44 → 0,58).

C'est un edge réel mais MODESTE en absolu (timing TSMOM long-only sur un actif macro
beta), et **EXAGÉRÉ par le rapport** qui le présente comme "carry-aligned trend"
(suggérant un edge orthogonal au beta).

### Robustesse en retirant les carry-unwinds

| Fenêtre | SR J1 | SR BH (passif) | Δ J1 |
|---|---|---|---|
| Full sample | 0,578 | 0,437 | — |
| ex-2008 | 0,589 | 0,494 | +0,01 |
| ex-2020 | 0,613 | 0,484 | +0,04 |
| ex-2008 & 2020 | 0,625 | 0,545 | +0,05 |
| ex-2008 & 2020 & 2022 | 0,560 | 0,492 | −0,02 |

Le 0,58 **SURVIT** aux retraits des crashes connus. Mais le buy & hold AUSSI
(0,44 → 0,55) — l'écart Δ_SR(J1 − BH) reste autour de 0,10-0,15 sur toutes les
fenêtres, **stable**. Donc le timing TSMOM apporte un edge réel mais qui ne croît
ni ne s'éteint en virant les unwinds. Robuste mais sans propriété spéciale
crisis-alpha.

---

## 3. Verdict G2 — Sensibilité ±50 % au swap modélisé

### Grille (book equal-risk J1+G1)

| Hypothèse | SR book |
|---|---|
| Baseline (mul=1, G1 swap orig) | **+0,71** |
| Baseline (mul=1, G1 swap symétrique = credit shorts) | +0,72 |
| **OPTIMISTE** J1 ×1,5 + G1 ×0,5 credit | +0,80 |
| **PESSIMISTE** J1 ×0,5 + G1 ×1,5 orig | +0,62 |
| Conservateur (mul=1,25 J1, orig G1) | +0,72 |
| NO-SWAP du tout | +0,65 (J1 perd 0,18, G1 gagne 0,08) |

### Décomposition du SR par le swap

| | sans swap | avec swap modélisé | Δ swap |
|---|---|---|---|
| J1 | +0,403 | +0,578 | **+0,175** (tailwind) |
| G1 | +0,761 | +0,679 | **−0,081** (headwind) |
| Book (equal-risk) | +0,65 | +0,71 | +0,06 net |

**Lecture :** 30 % du SR de J1 vient du carry encaissé hypothétique. Le proxy ^IRX
(T-bill 13w) **surestime** le vrai différentiel 2y US-JP (qui était plus bas pendant
les périodes de courbe US inversée 2022-2024), et le broker réel applique typiquement
une shave de 1,5-3× au mid. Si on accorde un haircut de 30 % au swap modélisé J1 (mul
≈ 0,7), J1 retombe à ~0,53 et le book à **~0,67**.

**Plus important :** le rapport admet une incohérence interne entre script (G1 ne
crédite pas les shorts) et inline (les crédite, écart ~+0,10 SR sur G1). La bonne
hypothèse pour un broker réel est **probablement asymétrique** (shorts non crédités
chez la plupart des CFD brokers, fully credited en futures). Comme G1 est en
pratique mostly long (Gold a un trend up sur 26 ans), l'impact est < 0,05 SR.

**Gate utilisateur :** "SR book < 0,5 sous hypothèse pessimiste plausible" → on
n'atteint pas ce seuil. **Pas KILL, mais drapeau jaune.**

---

## 4. Verdict G3 — Profil de queue du book

### Daily

| | std | skew | kurt | worst day | p1 | p5 | CVaR1 | CVaR5 |
|---|---|---|---|---|---|---|---|---|
| J1 (vol 10 %) | 0,63 % | −0,45 | +9,56 | −6,40 % (2024-07-11) | −1,83 % | −1,03 % | −2,58 % | −1,58 % |
| G1 (vol 10 %) | 0,63 % | −0,33 | +3,50 | −4,30 % (2026-01-30) | −1,81 % | −1,00 % | −2,37 % | −1,50 % |
| **Book (J+G u-vol)** | 0,90 % | **−0,36** | **+3,40** | **−6,26 %** (2005-12-14) | **−2,57 %** | −1,41 % | **−3,37 %** | −2,15 % |

Skew rolling 252j : médiane −0,34, **82 % du temps < 0** → structurellement et
durablement négatif. ≠ artefact d'un événement isolé.

### Mensuel ‼

| | skew_M | worst month | p1 mensuel | p5 mensuel |
|---|---|---|---|---|
| J1 | **+0,65** | −10,22 % (2024-07) | −5,03 % | −3,50 % |
| G1 | +0,08 | −6,24 % (2016-11) | −5,82 % | −4,09 % |
| **Book** | **+0,31** | −8,54 % (2022-11) | −7,90 % | −5,72 % |

**Le skew MENSUEL du book est POSITIF.** Daily skew négatif + monthly skew positif
= classique TSMOM (gros mois gagnants concentrent l'edge, queues daily petites).

### Top-10 worst days du book

| Date | Return | Année |
|---|---|---|
| 2005-12-14 | −6,26 % | 2005 |
| 2024-07-11 | −5,37 % | 2024 |
| 2026-04-30 | −5,17 % | 2026 |
| 2021-06-17 | −5,01 % | 2021 |
| 2019-01-03 | −4,61 % | 2019 (flash crash USDJPY) |
| 2002-03-07 | −4,35 % | 2002 |
| 2026-01-30 | −4,24 % | 2026 |
| 2017-03-16 | −4,04 % | 2017 |
| 2026-01-26 | −4,03 % | 2026 |
| 2015-08-24 | −4,02 % | 2015 |

**0 jour sur les top-10 dans 2008/2020/2022** (années "carry-crash" attendues du
rapport). Pertes **dispersées sur toute la période**. Le mythe "carry-crash
structurel sur 2008/2020 tue J1" est NON OBSERVÉ. (Le rapport dit MaxDD J1 = −27 %
mais n'attribue pas ce DD à une année précise — ce qui est en fait correct, juste
sous-estimé en termes de discours.)

### Pourquoi le trailing-stop a échoué (interprétation honnête)

Le rapport rapporte un échec du trailing-stop intraday (qui en plus avait un leak
bug SR 2,05→0,32). Hypothèse de l'auteur : "carry-crash gap-overnight
non-stoppable". **Cette hypothèse n'est PAS confirmée par les données.**

Test simple : si on applique un kill switch quotidien à −3 %, le SR **monte** de
+0,71 à +0,81 (Δ = +0,10). Donc une partie des pertes EST mesurable intraday et
peut être coupée — ce n'est pas que du gap. L'échec du trailing-stop dans le
rapport vient probablement de :
- une fenêtre de trailing trop serrée (whipsaw)
- un trailing-stop signal-level (sleeve) au lieu d'un kill switch hard cap (book)
- le bug look-ahead initial qui a faussé l'évaluation

**Le skew négatif daily est réparable à hauteur de +0,10 SR par un cap quotidien
hard** (pas par un trailing intelligent — c'est un patch, pas un signal). Cela ne
sauverait PAS p(pass) FTMO de manière dramatique (un cap −3 % à sizing 1,5 % laisse
encore −4,5 % par jour, on garde 60 % de la barrière 5 %) mais sur personal book
sans barrière daily, le profil est déjà sain (worst month book réaliste vol 10 % =
−6 %, gérable).

---

## 5. Verdict G4 — Pas de leak résiduel

| Délai (j) | SR J1 | SR G1 | SR book |
|---|---|---|---|
| −3 | 0,544 | 0,481 | 0,529 |
| −2 | 0,505 | 0,574 | 0,603 |
| **−1 (anti-causal)** | 0,558 | 0,629 | 0,638 |
| **0 (baseline)** | **0,578** | **0,679** | **0,708** |
| **+1 (futurisé)** | 0,458 | 0,488 | 0,490 |
| +2 | 0,500 | 0,510 | 0,539 |
| +3 | 0,475 | 0,520 | 0,513 |
| +5 | 0,484 | 0,474 | 0,537 |
| +10 | 0,609 | 0,609 | 0,697 |

Δ SR(+1) = −0,12 / −0,19 / −0,22 sur J1/G1/book → **dégradation cohérente**. PAS de
leak résiduel. Le pic résiduel à +10 (0,70 sur le book) est cohérent avec
l'autocorrélation lente d'un TSMOM 12-1 (la persistance dépasse 10 jours sans
problème) — pas un signe de bug, plutôt une signature de signal slow.

L'absence d'amélioration nette avec délai −1 (anti-causal, qui *devrait*
mécaniquement améliorer en triche pure) est cohérente avec un signal "slow" : voir
1 jour de plus dans le futur ne change rien quand le signal est mis à jour toutes
les ~20 séances. Ce comportement est attendu et rassurant.

---

## 6. Verdict G5 — Conteneurs

### (a) FTMO

**Confirmé clos.** Plafond ~36 % en 1 essai, mur structurel — cf
`_FTMO_ETAT_CANONIQUE.md` §3-7. **Pas re-prouvé** (hors scope ; sortir un chiffre
FTMO sur le book trend ne change rien au verdict canonique).

### (b) Personal book

| Sleeve | SR | MaxDD vol 10 % |
|---|---|---|
| A (Strategy A proxy : BTC TSMOM weekly LO) | **1,257** | −15,2 % |
| B (delta-neutral mainnet proxy) | ~2,0 (canonique) | −0,5 % |
| Book J1+G1 baseline (= rapport) | 0,71 | −22,7 % |
| Book J1+G1 realistic (swap×0,7) | 0,67 | −23,6 % |

**Corrélation book vs A proxy** :
- Daily : +0,004
- Weekly : +0,038
- Monthly : −0,027

**Décorrélation confirmée**, mais le sleeve est trop faible en SR pour améliorer
le portefeuille existant :

| Combinaison | SR_port (corr=0) |
|---|---|
| A + B seul | **2,355** |
| A + B + book baseline (0,71) | 2,331 (gain **−1,0 %**) |
| A + B + book realistic (0,67) | 2,311 (gain **−1,9 %**) |
| Gate D requis | > 1,10 × 2,355 = **2,59** |

**Sensibilité corrélation (book réaliste)** :

| corr book-A | corr book-B | SR_port |
|---|---|---|
| 0,0 | 0,0 | 2,31 |
| 0,1 | 0,1 | 2,17 |
| 0,2 | 0,2 | 2,05 |
| 0,3 | 0,2 | 2,00 |

Même à corr 0,0 partout, le book est dilutif. **Pas de qualification comme strategy
D.** L'arithmétique est simple : ajouter un sleeve à SR 0,7 à un portefeuille à SR
2,4 fait baisser le SR pondéré (à vol égale par sleeve), sauf si la décorrélation
est négative — ce qui n'est pas le cas (~0).

**Cas où le book devient utile** : si A reste gelé (Propr breach) et B retarde
(mainnet décalé après 2026-07), le book J1+G1 fournit un sleeve macro propre qui
peut tourner pendant les périodes d'arrêt. Pour ce cas, sizing modeste (vol cible 5
%) → worst month book réaliste à vol 5 % ≈ −3 %, gérable sur compte personnel.
**Mais c'est un by-default sleeve, pas un add-on portefeuille.**

### (c) CV

L'item CV n'est PAS "j'ai un book trend à SR 0,7". C'est :
- réplication propre d'un classique (TSMOM Moskowitz 12-1, formulation littérature non tunée)
- 2 bugs attrapés et documentés (look-ahead trailing-stop SR 2,05→0,32 ; blowup numérique CTA)
- décomposition honnête du sleeve : filtre carry démasqué comme cosmétique,
  alpha vs buy & hold quantifié à 0,14 SR (≈ +2,1 %/yr), sensibilité ±50 % au
  swap exposée
- skew profile honnête : daily −0,36 stable, mensuel +0,31, top-10 worst days
  dispersés (≠ carry-crash naïve)
- verdict portefeuille honnête : dilutif vs A+B malgré décorrélation, NO-GO
  comme strategy D
- 0 jour live, pas de pivot opportuniste

C'est exactement le profil méthodologique attendu en buyside quant. **À garder
comme item CV ; ne PAS le présenter comme "j'ai un book à 0,70 SR" mais comme
"j'ai vérifié un classique et exposé ses 5 fragilités structurelles".**

---

## 7. Limites & caveats (honnêteté)

1. **Proxy ^IRX pour le carry US-JP**, pas le vrai différentiel 2y US-JP (FRED
   inaccessible depuis cette session). Surestime probablement le swap réel
   2022-2024. Borne d'erreur ±20-30 % sur le swap → ±0,03-0,05 SR sur J1.
2. **Swap modélisé non mesuré sur broker.** L33 mandaté. Mesurer avant tout
   capital. Différentiel J1 sans swap (0,40) vs avec swap modélisé (0,58) =
   0,18 SR — le swap est *load-bearing* dans le SR rapporté.
3. **Données Yahoo Finance** (JPY=X, GC=F, BTC-USD). Yahoo FX a des glitches
   (3 corrigés sur JPY). Pour publication CV, refaire avec Bloomberg ou Refinitiv.
4. **0 jour live.** Tout backtest. Aucune validation d'execution réelle (slippage,
   gap-overnight CFD, intraday FX execution).
5. **Strategy A proxy approximé** : BTC TSMOM 28j weekly LO sans SOL/ETH (pour
   décorrélation : SR 1,26 vs 1,33 reporté, écart 5 %, acceptable comme proxy).
   La corr book/A vraie pourrait différer ; check à refaire quand fenêtre
   commune sera disponible avec la vraie série Strategy A.
6. **Strategy B SR 2,0** = proxy mainnet (cf L14). Vraie SR mainnet inconnue
   jusqu'à 60+ jours live (2026-07-17 estimé). Si SR_B mainnet < 2,0, l'impact
   sur l'évaluation du book change (book devient moins dilutif).

---

## 8. Conclusion (1 page)

**J1+G1 N'EST PAS un artefact de pipeline** (G0 PASS littéral, G4 PASS délai), mais
**N'EST PAS non plus l'edge que le rapport prétend** :

- Le filtre "carry-aligned" J1 est **cosmétique à 99,9 %** (G1) → J1 = TSMOM
  long-only sur USDJPY, sans propriété carry spéciale.
- Ce TSMOM long-only est **70 % beta carry-trade JPY** (β=0,51 vs buy & hold),
  avec un **alpha de timing modeste** de +2,11 %/yr (t=1,98 naïf, probablement
  ~1,7 en HAC).
- Le swap modélisé apporte **30 % du SR de J1** (G2) et n'a JAMAIS été mesuré.
- Le skew daily −0,36 est confirmé mais le skew MENSUEL est positif +0,31
  (G3) → problème spécifique barrière FTMO, pas personal book.
- "Carry-crash 2008/2020/2022 structurel" du rapport = **mythe** (0/10 worst
  days dans ces années) (G3 bis).
- Apport au portefeuille A+B = **dilutif** (G5) : SR_port baisse de 2,36 à 2,31.

**Trois conteneurs, trois verdicts** :

| Conteneur | Verdict |
|---|---|
| **FTMO** | Confirmé clos (cf canonique). Hors scope. |
| **Personal book add-on à A+B** | **NO-GO**. Dilutif (gate D : 2,59 requis, 2,31 atteint). |
| **Sleeve de secours si A gelé + B retardé** | OPTIONNEL à vol 5 %, worst month ~−3 %. |
| **CV** | **OUI**. Pas pour le SR 0,7, mais pour la méthodologie (réplication propre + 2 bugs + 5 fragilités exposées). |

**Banque d'apprentissages** (L candidates) :

- **L37 (proposé)** — *Filter sanity check* : avant de présenter un sleeve avec
  filtre conditionnel (carry-aligned, regime-conditional, etc.), compter la
  fraction du temps où le filtre **agit effectivement** (signe(filtre) ≠ signal
  natif). Si < 5 %, le filtre est cosmétique — appeler le sleeve par son nom
  réel (ici : "TSMOM long-only", pas "carry-aligned trend").
- **L38 (proposé)** — *Beta-orthogonal test* : pour tout sleeve d'allure
  "structural premium", régresser sur un buy & hold vol-targeté de l'asset
  primaire et reporter (β, α HAC, R²). Si R² > 30 %, ce n'est PAS un edge
  orthogonal — c'est du timing sur beta. Le présenter comme tel.
- **L39 (proposé)** — *Daily vs monthly skew dissociation* : sur strategies
  trend/carry, daily skew peut être négatif et monthly skew positif simultanément.
  Le skew DAILY importe sur barrière daily (FTMO 5 %) ; le skew MENSUEL importe
  sur drawdown rule mensuel + personal book sans barrière intraday. **Ne pas
  conflater** — toujours reporter les deux.

---

## 9. Artefacts produits (data/trend_research/)

| Fichier | Rôle |
|---|---|
| `g0_replication.py` | Réplication indépendante (log-ret, lag t-1) → SR 0,47 |
| `g0_twin_check.py` | Twin littéral du script du rapport → SR 0,70 ✓ |
| `g0_pnl.csv`, `g0_twin_pnl.csv` | Séries PnL pour gates suivants |
| `g1_j1_vs_long_jpy.py` | Test filtre carry + OLS J1 vs buy & hold |
| `g1_sleeves.csv` | Toutes les variantes J1 (aligned, unfiltered, LO, BH ±swap) |
| `g2_swap_sensitivity.py` | Grille swap mul ∈ {0.5,…,2.0} × variantes G1 |
| `g2_swap_grid.csv` | Grille brute |
| `g3_skew_tail_profile.py` | Stats tail daily/monthly + top-10 worst days + kill switch test |
| `g3_book_book.csv` | Book vol 10 % normalisé |
| `g4_delay_leak.py` | Grille délais [−3, +10] |
| `g4_delay_grid.csv` | Grille brute |
| `g5_container_verdict.py` | Corr book / A proxy + apport portefeuille |
| `g5_book_vs_A.csv` | Book réaliste + A proxy pour audit |
| **`trend_verification_2026-06.md`** | **CE document** |

Tous les scripts utilisent `/usr/bin/python3` + numpy/pandas standard. Yahoo
Finance pour les sources de données. Aucun import du script `trend_replication.py`
fourni — réécriture indépendante puis twin littérale pour cross-check.
