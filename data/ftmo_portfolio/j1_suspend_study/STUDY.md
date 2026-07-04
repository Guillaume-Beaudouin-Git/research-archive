# STUDY — J1 (USDJPY) suspension en zone d'intervention : résultats

Pré-registration gelée : `PREREGISTRATION.md` (commit `bdf7281`, AVANT résultats).
Harnais EQUIV réutilisé de la levcap study (hooks inertes). Chaîne v2.2.1 gelée (yaml `56fbdde7`).
**Read-only, rien déployé.** Auteur : session 2026-07-03. **Audit indépendant : EN ATTENTE**
(sous-agent bloqué par limite de session ; auto-vérif faite, voir §5).

## 1. Verdict
**DÉPLOYER la suspension ciblée (gate en zone), PAS la suspension permanente.** Le gate
opérationnel (OFF si USDJPY ≥ 160, reprise après 10 closes ≤ 155) est **abordable — en fait
légèrement positif et strictement à sens unique** (aide 3 cohorts, n'en pénalise aucune), tandis
que retirer J1 en permanence coûterait **−7.58 pts / −$88** (J1 est un vrai diversifiant). Le gate
**cible** la suspension exactement quand le risque de queue est vivant, en conservant 99 % de la
valeur de diversification de J1.

## 2. Triplet (challenge, 462 cohorts, EQUIV PASS 87.01)
| Arm | p_pooled | p_IS | p_OOS | attempts | Δp [CI90] | ΔEV [CI90] | pire gap J1 |
|---|---|---|---|---|---|---|---|
| baseline | 87.01 | 90.56 | 83.41 | 3.24 | — | — | −$2,822 |
| **FULLOFF** (J1 off partout) | 79.44 | 78.54 | 80.35 | 3.03 | **−7.58** [−12.99, −2.81] | **−$87.6** [−171.5, −11.4] | $0 |
| **GATE160** (opérationnel) | 87.66 | 90.56 | 84.72 | 3.21 | **+0.65** [0.00, +1.95] | **+$12.6** [$0.0, +35.2] | −$2,822 |
| GATE158 (sensibilité) | 87.66 | 90.56 | 84.72 | 3.21 | +0.65 [0.00, +1.52] | +$12.4 [−0.6, +30.9] | −$2,822 |

CI = bootstrap bloc circulaire apparié (blocs=10 cohorts, 3000 tirages, seed=23 ; N_eff=173.7).
VAL=$1,422, FEE=$96 (convention v2.2/v2.3). EV = funded·VAL − attempts·FEE.

**Règle de décision (gelée) : AFFORDABLE** = Δp CI90 ≥ −2.0 pts ET ΔEV CI90 ≥ −$40.
GATE160 : Δp CI90 lo = **0.00** ≥ −2.0 ✓ ; ΔEV CI90 lo = **$0.00** ≥ −$40 ✓ → **AFFORDABLE = VRAI**
(par large marge — non-négatif sur p ET EV à 90 %).

## 3. Mécanisme du +0.65 (une seule direction)
GATE160 fait basculer **exactement 3 cohorts, toutes de échec→réussite** (starts 2024-05-23,
06-03, 06-12 — toutes OOS, « en vol » quand USDJPY a coiffé ~160 en 2024-06). **0 cohorte
pénalisée.** Suspendre J1 long pendant le top yen a évité des pertes J1 et converti 3 quasi-échecs
en fundeds. 19 cohorts « touchées » (fenêtre chevauchant ≥1 jour OFF), 3 basculent, 16 neutres.
Robuste au seuil : 158 (193 j OFF, 46 touchées) donne le MÊME +0.65 → le sur-suspendre est neutre.

`risk_jpy 0.288→0.000` sous FULLOFF (avec `risk_gold 0.323→0.438`, `risk_on_us 0.285→0.386`)
confirme l'unique canal de re-levier = **relâchement du margin-cap 60 %** (les 3 autres jambes
remontent vers leur cible propre), exactement comme prédit au Volet 1. Bénin, borné.

## 4. Queue gauche — donnée (rétrospectif) vs jugement (prospectif)
**RÉTROSPECTIF (le MC ne peut pas voir la queue) :** pire gap week-end J1 = **−$2,822 en baseline
ET en GATE160 (INCHANGÉ)**. Le pire gap J1 in-sample (Grexit 2015-06-29) n'est **PAS** un jour
USDJPY-zone → le gate ne le touche pas, exactement comme pré-enregistré. Le pire jour BOOK
(−$7,078) est la sleeve OVERNIGHT, hors J1. **Δqueue in-sample du gate ≈ 0.** Le MC finit
2026-06-05, max close 161.57 : le flash d'intervention 2026 est **hors-modèle**.

**PROSPECTIF (jugement, arithmétique au notionnel live) — le vrai motif du gate :**
gap USDJPY overnight adverse, notionnel du breach (1.73 lot = $173k = 16.8× ; $1,067/yen) vs
LCAP8 ($494/yen) vs suspendu ($0). Floors : daily −$500, static −$1,000.
| gap overnight | J1 @16.8× (live) | J1 @LCAP8 | J1 suspendu |
|---|---|---|---|
| −0.5 yen (≈ le breach réel, −$527) | −$534 → **BUST daily** | −$247 (ok) | **$0 → survit** |
| −1 yen | −$1,067 → **BUST floor** | −$494 (bord daily) | **$0 → survit** |
| −2 yen | −$2,136 → **BUST floor** | −$988 (bord floor) | **$0 → survit** |
| −3 yen | −$3,204 → **BUST floor** | −$1,482 → **BUST floor** | **$0 → survit** |
→ Au sizing live, même −0.5 yen tue. LCAP8 encaisse −0.5/−1 mais casse à −2+. **Seule la
suspension survit à un gap multi-yen** (confirme levcap Q4 « cap ET suspendre »). C'est un
jugement de risque, pas un edge backtesté.

## 5. Vérification (auto — indépendante EN ATTENTE)
Re-dérivé indépendamment des CSV bruts (pas via aggregate) : grids identiques 3/3 ; pooled
0.8701/0.7944/0.8766 ; Δp −7.58 / +0.65 ; 3 flips tous échec→réussite, tous OOS post-2024 ;
FULLOFF −7.58/−$88 = la valeur d'ablation J1 v2.3/levcap connue (cohérence externe). Gate
re-testé avec une impl fraîche (80/79 j, shift(1) → pas de look-ahead). **EQUIV PASS 87.01** =
le harnais reproduit la chaîne canonique. **À FAIRE : audit sous-agent indépendant** (author≠auditor)
au reset de session — re-checker EQUIV + gate + deltas + honnêteté cost-vs-tail.

## 6. Limites (déclarées)
- Le MC ne price PAS la queue (hors-modèle) ; la valeur de protection est prospective (2 breaches
  + §4). Le backtest ne fait que **dégager le coût** (≈0), il ne **prouve pas le bénéfice**.
- +0.65 pts repose sur 3 cohorts (petit N) — traiter comme « ≈ gratuit », pas comme un edge.
- Suspension ≠ dispense de sizing : à 16.8×/$180k un gap multi-yen casse même capé (levcap Q4).
  Le gate protège en coupant l'exposition ; il ne corrige pas le sizing.
- Live intraday : le gate gèle sur close ≤ T-1 (reproductible, matché au backtest) ; option
  conservatrice = lire aussi le niveau intraday à 21:50 (non retenu pour la reproductibilité).
