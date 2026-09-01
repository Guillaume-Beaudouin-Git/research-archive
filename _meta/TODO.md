# TODO — état au 2026-09-01

Consolidé après la session desk (dossiers ORB + overnight, diagnostic de régime, contexte macro,
enquête Dédale). Le nettoyage du dépôt est **terminé** ; ce qui reste est de la décision, de la
dette de méthode et deux gestes opérateur. Classé par échéance réelle.

---

## 🔴 Septembre — échéances dures

| # | tâche | qui | critère de fin |
|---|---|---|---|
| 1 | **Premier payout** — repasser **au-dessus de 10 000** avant la frontière des 14 jours de trading (`open_days`=10 au 01/09). Déclenche le retrait ET les **99 €** de remboursement du challenge. Balance au 01/09 : **9 931,55**. | **toi** | payout demandé |
| 2 | **Compléter la mesure de dérapage ORB** — 12 observations restantes (18/30 faites), ~1/jour ouvré ⇒ **~18 septembre**. Décide QUAND désarmer, pas SI. | automatique | N=30 |
| 3 | **Ré-ancrer les 4 swaps** (`spec_bounds_breach = 1`, dérive > 25 % sur les 4 jambes). Impact P&L faible mais **le swap de l'or est DANS le signal**. Chaîne complète : config → yaml → sha → mqh → recompile → dépôt. **Fenêtre SAMEDI, binaire AVANT le merge.** | moi (prépa) + toi (déploiement) | pins à jour |
| 4 | **Merger les branches de la session** — `desk-orb`, `desk-overnight`, `regime-diag`, `macro-context`, `funded-numbers`, `macro-deepdive`, `dedale-{strategy,config,audit,broker,data,notebooks}`, `brieuc-replication`, `orb-variants`, `momentum-intraday`, `audit-ledger-orb`. | toi | 0 branche en attente |

---

## 🟠 Octobre — la décision ORB

**Cadre déjà établi, il ne manque que le coût final.**

| coût final tout-compris | action | justification |
|---|---|---|
| < 1,69 bps | *(improbable)* long-only | il faudrait ≤ 0,098 bps sur les 6 AR restants |
| **1,69 – 2,17** | **long-only, dérogation resserrée** | position actuelle (2,11 bps) |
| > 2,17 | **désarmer** | il suffit de 1,298 bps, soit **+13 %** du dérapage observé |

**La jambe courte est déjà condamnée indépendamment du coût** : t = 1,246 en **brut** (coût nul),
la rupture 2022 qui la justifiait est au 73ᵉ percentile du bruit (p = 0,266), puissance 12 % sur
2022-2026, effet sous son propre MDE, DSR ≈ 0,0000. Le bêta de la jambe longue est réel
(β = +31,7, R² 17,8 %) mais **sous** le seuil disqualifiant de 30 %.

- [ ] Trancher ORB à N=30 observations de dérapage
- [ ] Nettoyer les worktrees (`.worktrees/`) une fois les branches mergées

---

## 🟡 Novembre-décembre — construction

- [ ] **Ouvrir le compte IBKR** — **chemin critique de ~2 semaines**. La fenêtre month-end est
      mensuelle : chaque mois d'attente coûte une occasion.
- [ ] **Déployer le month-end ZN** — 1 contrat, marge ~$1 800 (**14 %** d'un compte de €13k),
      **+17,6 %/an**, Sharpe 0,92 net, pire événement historique **−15,5 %**, exposé 14 % des jours.
      Plan complet : `_meta/plan_book_perso_2026-08.md`.
- [ ] **Session dédiée FX carry (« Dédale revisité »)** — rejouer l'idée avec (a) swaps historiques
      réels, (b) filtre de carry par trade et non figé, (c) two-sided réellement autorisé,
      (d) sous les différentiels de 2026. Mémoire : `fx_carry_dedale_2026-08`.

---

## 🔵 Dette de méthode — sans échéance

- [ ] **Résurrections S037 / S061** du corpus 109 (l'audit d'ambiguïté les fait passer DISCARD → KEEP ;
      S061 fragile au contrôle L60). Δn_tests = 0.
- [ ] **Coût natif COPPER** — seule des 4 commodités dont la marge (×27) n'est pas hors d'atteinte
      d'une erreur de source. Ferme proprement le kill énergie.
- [ ] **CI** : `GARDE 1` de `auto-merge.yml` sort en `exit 1` **avant** l'étape qui pose le label
      `needs-human-review` ⇒ une PR bloquée n'est jamais étiquetée. Le blocage est réel, seule la
      signalisation manque.

---

## ✅ Clos pendant cette session

- **Calendrier overnight lundi+mardi** — dette DSR 0,29 ouverte depuis le 2026-06-03 et signalée
  dans 5+ documents : **TRANCHÉE ET CLOSE** (`_meta/decision_calendrier_overnight_2026-09.md`).
  Restriction maintenue : c'est une **contrainte de coût**, pas une sélection de signal
  (toutes-nuits = **−0,17 bps** sur GER40, **+0,36** sur US100 ; lundi+mardi = **+5,11/+4,49**).
- **L64 et L65 gravées** au registre (48 leçons) : rupture temporelle **estimée et non imposée**,
  corrigée du balayage ; MDE calculé avec la **puissance** (facteur 1,40).
- **Enquête Dédale** — mécanisme entièrement compris, biais d'anticipation démontré, version non
  biaisée chiffrée (+16-21 % contre +60,33 % revendiqués).

---

## 📌 Rappels de contexte

- **Le livre est MONO depuis 27 jours-cerveau** : or éteint par vote 2-1 des lookbacks
  (|sig| 0,3333 < 0,34, unanimité requise), USDJPY éteint par porte à hystérésis
  (coupe 160 / rallume **155** après 10 clôtures ; niveau 160,09). **Rien à forcer** — ce sont
  des états de régime, pas des pannes.
- **Un drawdown de 1 % touche 100 % des cohortes**, ~12×/an, **94 % se recouvrent en 22 j**.
  Le seuil qui change de nature est **−5 %** (24 % des cohortes, seulement 40 % en reviennent, 206 j).
- **Si le risque doit baisser : réduire `ea_on_w`, jamais retirer un jour** (L54 — le dé-levier
  plat domine tout conditionnement, vérifié sur ce sleeve).
- **n_tests cumulé ≈ 1 999**, seuil Šidák |t| ≈ 4,21.
