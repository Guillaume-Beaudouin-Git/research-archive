# Intraday-Flat Corner — session_G_intraday_flat — Exploration 2026-06
*Thèse (L36, session_F) : sur FTMO le carry overnight (~8 %/an) pré-tue toute prime tenue overnight/multi-jour ; la
SEULE structure carry-immune est **intraday-flat** (flat à la clôture → zéro swap). Mais l'intraday FTMO est l'espace
le plus miné de l'arc (~350 MR + 176 momentum + 190 breakout ≈ 700 candidats, 0 survivant). Cette session **ferme
proprement** le coin intraday-flat avec les candidats les moins minés. **Prior bas, négatif propre = livrable de clôture.**
Coût décisif (L33-bis) : zéro swap, mais le **spread intraday décide** → spread CONSERVATEUR **3 bps RT, flaggé**.
Gates : délai-1 (L26, arbitre), two-sided (L25), OOS (L31), N (L12), DSR (N_tests cumulé ~O(150) → barre ~|t|>3).
Instrument : NQ=US100, databento, vrai UTC, barres minute RTH 2010-2026. Périmètre : écrit UNIQUEMENT `session_G_intraday_flat/`. Rien figé/mergé.
Code : `code/skew_sessionG.py`.*

## SG-1 — Continuation intraday post-release (flat close)
*Distinct du pré-FOMC run-UP (décayé) ; ici = la continuation APRÈS le print. FOMC 14:00 ET (rth_min 270, intraday) ;
CPI/NFP 08:30 ET (pré-RTH → gap-continuation open→close).*

| Test | n | mean net | t net | skew | Verdict |
|---|---:|---:|---:|---:|:--:|
| FOMC continuation (react 270→285, trade 285→close) NET 3bps | 51 | +0,5 bps | +0,03 | −0,79 | ❌ |
| …react UP (long) / react DOWN (short) | 21/30 | +7,3 / +0,8 | 0,28 / 0,03 | — | ❌ pas two-sided |
| …**OOS 2020-2022** / **2023-2026** | 24/27 | **−37,5** / **+34,2** | −1,25 / +1,95 | — | ❌ **sign-flip** |
| CPI/NFP gap-continuation (open+5min→close) NET 3bps | 146 | +6,5 bps | +0,69 | −0,50 | ❌ sous-seuil |
| …gap UP / gap DOWN (two-sided) | 85/61 | +9,7 / +9,1 | 0,96 / 0,51 | — | bonne forme, non-signif |

- **FOMC** : full-sample mort (t=0,03). Le **sign-flip** 2020-22 (−37) vs 2023-26 (+34) est le **tell d'absence d'edge
  stable** ; cherry-pick le récent (t=1,95) serait du data-snooping → échoue la barre DSR (t≈3) + N=27 (L12). MORT.
- **CPI/NFP** : seule à avoir la **bonne forme** (two-sided positif : +9,7 gap-up, +9,1 gap-down) mais **sous-seuil**
  (net t=0,69). Effet réel-mais-minuscule **mangé par le spread**, ou bruit. Pas déployable.

## SG-2 — Gao time-of-day momentum (re-run propre)
*1ère demi-heure → dernière demi-heure (Gao-Han-Li-Zhou). Recoupe « intraday-momentum (176) » mort + session_3 C3 (t=−0,13). Re-run protocole anti-mining.*

| Test | n | mean net | t net | skew | Verdict |
|---|---:|---:|---:|---:|:--:|
| sign(first30)×last30 RAW (gross) | 3978 | −0,0 bps | −0,08 | +0,19 | ❌ (confirme C3) |
| …**NET 3bps** | 3978 | **−3,0** | **−6,08** | +0,19 | ❌ spread exécute |
| two-sided : last30 \| first30 UP / DOWN | 2081/1872 | −0,1 / +0,1 | −0,22 / +0,08 | — | ❌ **aucune jambe** |
| OOS pré-2015 / 2015-19 / 2020-26 NET | 1135/1247/1596 | −2,9 / −2,7 / −3,4 | −3,8 / −4,0 / −3,5 | — | ❌ mort toutes périodes |

Gross ≈ 0 (pas d'edge, même pré-2015), **net −3 bps (t=−6)** : le spread 3 bps **exécute** le signal. Échoue le
two-sided (L25) de façon décisive (ni long ni short ne marche). **Mort robuste.**

## DSR / N_tests
N_tests cumulé sur l'arc ~O(150) → barre multiple-testing ~|t|>3 (Bonferroni z). **Aucun candidat n'approche** :
meilleur brut = FOMC-2023-26 t=1,95 (sous-période cherry, N=27) et CPI/NFP t=0,69. Tous **sous la barre DSR**.

## VERDICT session_G — le coin intraday-flat est VIDE
Les deux candidats les moins minés meurent : FOMC continuation = **pas d'edge stable** (sign-flip, DSR-fail, N≈L12) ;
CPI/NFP = bonne forme mais **sous-seuil** ; Gao = **net-négatif au spread + échoue two-sided + mort toutes périodes**.
→ **Le coin intraday-flat ne contient PAS de survivant — vide comme le reste de l'intraday FTMO.** Coin **CLOS proprement.**
Le carry-immunité (zéro swap) ne suffit pas : le **spread** prend le relais comme tueur (L33-bis), et les signaux
intraday-flat résiduels n'ont pas l'amplitude (>3 bps gross) pour le franchir.

## Candidats-leçons (NOMMÉS)
> **LESSON-CANDIDATE: intraday-flat-corner-is-empty** — la structure carry-immune (intraday-flat, zéro swap) — seule
> échappatoire à L36 — ne livre **aucun survivant** : FOMC-continuation sign-flip (pas d'edge stable), CPI/NFP sous-seuil,
> Gao net-négatif + échoue two-sided. Le graveyard intraday FTMO (~700) s'étend à l'intraday-flat. Coin clos.

> **LESSON-CANDIDATE: spread-is-the-intraday-executioner (L33-bis)** — en intraday-flat le coût liant n'est PAS le carry
> (zéro swap) mais le **spread** : Gao a ~0 gross mais **−3 bps/t−6 net** au spread conservateur 3 bps. Un signal
> intraday-flat doit avoir **>3 bps gross** pour survivre — les candidats les moins minés ne l'ont pas.

> **LESSON-CANDIDATE: sub-period-sign-flip-is-not-an-edge** — FOMC continuation 2020-22 (−37) vs 2023-26 (+34) :
> isoler la moitié récente positive (t=1,95) serait du data-snooping. Sign-flip + full-sample≈0 + DSR (t>3) + N petit
> = mort. La stabilité inter-période est un gate, pas un détail.
