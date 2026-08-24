# STUDY — Métriques RÉELLES du book (compte 3, <ACCOUNT_ID>) : gate J1 + low-check

Pré-reg gelée `PREREGISTRATION.md` (commit `9a07bc7`, AVANT résultats). Moteur canonique
(`engine_v22`, chaîne v2.2.1) **NON muté** — low-check = overlay d'évaluation. Read-only, aucune
action live. Auteur : session 2026-07-06. **Audit indépendant : voir AUDIT.md.**

## 1. Verdict (le triplet réel)
**Compte 3 = SWING + gate J1 ON + low-check au bid** (données → 2026-06-05, 462 cohortes) :

| métrique | valeur | note |
|---|---|---|
| **p(pass challenge)** | **69.7 %** | [69.7 all-legs, 70.4 dominant-leg] ; baseline cité 71.4 % |
| **essais / campagne** | **3.29** | challenges achetés dans une campagne 91 j |
| **temps médian → funded** | **38 j** | par campagne réussie |
| **p(funded = pass P1+P2 en 3 mois)** | **69.7 %** | ≡ p(pass) : passer = devenir funded |
| **EV / campagne** | **+$678** | [+678 all-legs, +733 dom] ; baseline cité +$740 |

Re-purchase (rachats jusqu'au 1ᵉʳ pass, MC 20 000 tirages) : **E[campagnes]=1.44** (1/p=1.43),
**E[challenges]=4.74**, **E[temps total]=88 j** (médian 56, p90 195).

**Correction d'optimisme = 71.4 → 69.7 = −1.7 pt** (EV +740 → +678 = −$62). **Petite et
non-significative** (CI90 enjambent 0). Décomposition ci-dessous.

## 2. Décomposition (SWING, pts, block-boot seed23, apparié par cohorte)
| effet | Δp | CI90 | lecture |
|---|---|---|---|
| **gate seul** (ON/close − OFF/close) | **−0.43** | [−1.30, 0.00] | ~neutre in-sample ; le +0.65 POLICY ne survit pas au de-levering SWING |
| **low-check seul** (OFF/low − OFF/close) | **−1.30** | [−4.11, +1.52] | bracket [−0.65 dom, −1.30 all-legs] ; petite |
| **combiné = compte 3** (ON/low − OFF/close) | **−1.73** | [−4.76, +1.08] | bracket [−1.08 dom, −1.73 all] |

**Le gate est EV-neutre-à-positif** : challenge ~neutre (−0.43), mais funded VAL 1438→1486 (moins de
drawdown J1 en zone 2024) → **EV gate seul +$768 > baseline +$740**. La valeur du gate est
PROSPECTIVE (queue hors-échantillon, cf. §5), pas in-sample.

## 3. Pourquoi la correction low-check est PETITE (le point clé)
Volet 0 a établi empiriquement que **`sim_m5` (canonique) ≡ `deep_history_utc` localisé Europe/Paris**
(median|Δ| close = **0.00000**, 4 legs — MÊME donnée sous-jacente, pas MT5-vs-Duka). Conséquence :
- Le low-check historique mesure l'effet **PUR intra-barre** (low franchit le floor mais le close
  recouvre), SANS confusion de source.
- Sur une source cohérente, **le M5-close capture DÉJÀ les flashs soutenus** (ex. 07-02 réel : le
  M5-close Duka buste à 06:45, cf. j1_m1_failure). Le low-check n'ajoute que les **spikes recouvrés
  sous-5-min** — rares. → correction petite (−0.65 à −1.30 pt).
- L'« optimisme absolu » qu'annonçaient les études j1 (« 71 optimiste ») venait surtout de
  l'**artefact de SOURCE MT5** sur le flash LIVE 07-02 (grid 06:50 = 161.795 near-miss), qui ne
  contamine PAS le MC historique (sim_m5 = Duka). Le low-check sur source cohérente le confirme.

**Nuance importante — pré-reg raffinée (documentée) :** la pré-reg §5 testait floor ET breaker sur
l'adverse (« low_both »). Raffinement vers le RÉALISME (postmortem breach, author≠auditor approuvé) :
le **floor FTMO est CONTINU** (le monitor a liquidé 06:49:41 entre deux regards M5) → testé sur
l'adverse ; le **breaker EA est DISCRET-M5** (`InvariantCheckM5`, OnTimer, ne voit pas l'intra-barre)
→ testé sur le close. Le primaire **« low » = floor-adverse / breaker-close**. « low_both » (donne au
breaker une vue intra-barre qu'il n'a pas → whipsaw) est reporté comme **borne pessimiste**
(compte 3 = 67.5 %, Δ −3.9 pt, toujours CI⊃0).

## 4. Risque résiduel — où vit le tail intra-barre NON couvert par le gate
**Le gate (J1 suspendu si USDJPY≥160) couvre 0 % du tail intra-barre in-sample** : 0/532 busts
low-check (challenge) et 0/58 (funded) tombent EN zone. Le tail est **hors-zone et réparti** :

| stade | busts low-check | sleeves dominants (all-legs) | dominants (borne dom-leg) |
|---|---|---|---|
| challenge (ON) | 532 (0 en-zone) | USDJPY 179 / XAU 158 / US100 147 / GER40 48 | — |
| **funded (ON)** | **58/191 = 30 %** | USDJPY 36 / **XAU 22** | **XAU 22** / USDJPY 4 |
| funded dom-leg | 26/191 = 14 % | — | XAU 22 / USDJPY 4 |

→ **Le carrier le plus ROBUSTE du tail intra-barre = l'OR (XAU)** (survit à la borne dominant-leg),
puis les **flashs USDJPY HORS zone** (<160, ex. 2016/2019/2022), puis US100/nightly. Le gate protège
J1-EN-zone, qui in-sample est ~vide. **Prochain angle mort = queue intra-barre de l'OR + JPY
hors-zone**, non couverte par le gate actuel.

**Stade funded = le vrai siège du tail** : 14–30 % de busts intra-barre vs 3 % au M5-close (×4.7 à
×10), car funded est vm1 (la marge SWING ne bind jamais à vm1 → positions PLEINES, pas de-levered
comme le challenge). Dégât $ BORNÉ : busts tardifs (median life 169 j, 93 % conservent des retraits
bankés, median $1161) → VAL ne chute que de 1438→1425.

## 5. Queue — donnée (rétrospectif) vs jugement (prospectif)
- **RÉTROSPECTIF (MC 2013-2026)** : le tail intra-barre est hors-zone (§4) ; le gate n'y touche pas ;
  correction low-check petite (§3). Les 2 flashs réels 07-02/03 sont HORS fenêtre (data → 06-05).
- **PROSPECTIF (jugement)** : les 2 breaches réels (<ACCOUNT_ID> 02/07, <ACCOUNT_ID> 03/07) étaient EN zone
  (USDJPY 161-162, gate armé). Les études j1 (m1_failure + lcap8, author≠auditor approuvées) ont
  établi que **le gate aurait suspendu J1 → les DEUX évités**. C'est la valeur du gate : une queue
  d'intervention EN zone qui ne s'est matérialisée que LIVE, pas dans le backtest. Cohérent avec le
  Δ gate in-sample ≈ 0.

## 6. Extension → 2026-07-06 (traitement honnête)
Data (sim_m5) → 2026-06-05. **Dernier start complétable = 2026-03-06** (mur 91 j) ; la fenêtre config
(OOS→02-25) capture déjà ~tout (extension = +1 cohorte). Un fetch → 07-06 ajouterait ~4 cohortes
mars-avril 2026 spanning les flashs — mais dans le régime ≥160 le gate garde J1 **flat** → ces
cohortes sont insensibles aux flashs sous gate ON (le flash ne mord qu'en arm OFF). Impact pooled
< bruit (4/462). **Fetch non exécuté** (symboles Dukascopy indices fragiles + valeur marginale nulle
sur le triplet + flash déjà répliqué par j1). Réintégrable sur demande.

## 7. Anchors de validation (tous PASS)
- **G-tz** : Duka-M5-close == sim_m5 close, median 0.00 bps / 4 legs (US100 seam immunisé par
  range-offset).
- **G-EQUIV** : `lowcheck(mode=close)` == `engine_v22` sur 462 cohortes (funded/attempts/t identiques)
  + px_day bit-identique + lo≤close≤hi.
- **POLICY anchor** : OFF/close = **87.01** (exact), gate = **+0.65** [0.00,+1.95] (reproduit la
  suspend study à l'identique).
- **SWING anchor** : OFF/close = **71.43 %** (= 71.4 cité) + EV **+$740** (= +740 cité) sous stack
  recost (swaps mesurés + commissions).

## 8. vm14 (SIGNALÉ, pas tranché)
Le low-check déplace-t-il l'optimum de sizing ? **Signal OUI au stade FUNDED** : le tail intra-barre
funded (14-30 % vs 3 %) est bien plus lourd que le M5-close ne le montre, et il est vm-sensible
(vm1 plein). Au stade CHALLENGE, l'effet est petit (book de-levered SWING). → une re-mesure vm14
sous low-check pourrait favoriser un funded plus prudent (dégât borné par le banking, mais bust=perte
du compte). **Chantier séparé — NON tranché ici** (conforme pré-reg §8).

## 9. Caveats (gelés, cf. pré-reg §9)
Low-check discret (flash sous-M1 non modélisé) ; surestime la perte (liq≈floor, pas le low → détecte
le bust, pas la perte exacte) ; all-legs = borne haute (legs se hedgent en risk-off), bracketé par
dom-leg ; niveaux absolus « indicatifs », seul le **Δ** robuste ; gate figé sur close T-1.

## 10. Audit indépendant (author≠auditor) — voir AUDIT.md
**VERDICT : CONFIRM-WITH-CAVEATS.** Toutes les ancres (87.01/+0.65/71.43/+740), le triplet compte-3
(69.70 / 3.29 / 38 j / +$678), la re-purchase, toute la décomposition + CI, les 2 gates (G-EQUIV 0/462,
G-tz median 0.0 sur un jour NEUF 2024-05-15) et l'attribution résiduelle **reproduits à l'identique**
depuis les données brutes (seed indépendant + McNemar corroborant la non-significativité). Le check
adversarial décisif (« le low-check est-il silencieusement supprimé, gonflant à tort la petite
correction ? ») = **NON** : offsets réellement appliqués (lo<close strict sur ~100 % des barres
couvertes). Réserves d'audit (interprétation, toutes déclarées) :
- (a) Échantillon → 2026-06-05 : USDJPY≥160 sur seulement 14 jours in-sample (tous 2024-06+) → le
  « gate ≈0 in-sample / 0 %-en-zone » reflète en partie un échantillon PAUVRE EN ZONE ; la valeur du
  gate est prospective, PAS prixée dans le 69.70 %.
- (b) Le primaire « low » est le plus clément des deux arms ; garder low_both (−3.9 pt, 67.5 %) en vue
  (conclusion inchangée, CI⊃0 aussi).
- (c) **Couverture M5 lo/hi** : XAU 94.3 %, USDJPY 99.9 % (carriers dominants BIEN couverts) ; US100
  83.7 %, GER40 83.0 % (barres non couvertes → fallback lo=hi=close = conservateur vers MOINS de busts
  → tail US100/GER40 possiblement légèrement SOUS-estimé ; n'affecte pas les carriers robustes XAU/JPY).
