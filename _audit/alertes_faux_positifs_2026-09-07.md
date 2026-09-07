# Diagnostic des alertes Telegram — 2026-09-07

Trois alertes reçues en rafale. **Aucune n'indique un problème de trading.** Diagnostic à la source
sur le VPS. L'EA est vivant (`state.json` à `2026.09.07 13:07:49`), pas de kill-file, compte à
9 903,08 avec 903 $ sous le plancher statique.

---

## 1. « EA erreur/reject: stop US100.cash ret=10015 Invalid price » — **FAUX POSITIF, champ périmé**

`last_error` dans `state.json` vaut cette chaîne. Mais **l'erreur n'apparaît dans AUCUN journal MT5
du 28 août au 4 septembre** — elle est donc antérieure au 28 août, et re-criée toutes les heures
depuis.

La cause est documentée dans le superviseur lui-même (`supervisor.py:369-372`) :

> « l'EA ne vide PAS `g_last_error` au réarmement (`mq5:1487` remet `g_killed=false` sans toucher
> `g_last_error`) → champ **« dernière erreur connue »**, pas **« erreur courante »** »

Le correctif existant ne couvre **qu'un cas** : la notice de désarmement « kill-file FLAT ». Toute
autre erreur reste dans le champ **à vie** et re-alerte toutes les 60 minutes indéfiniment.

**Correctif proposé (Python seul)** : cooldown **escaladant** sur erreur identique — 60 min au
premier déclenchement, puis 24 h, puis 7 jours. Une erreur qui persiste sans se renouveler cesse de
crier ; une erreur **nouvelle** (hash différent) alerte immédiatement comme aujourd'hui.
⚠ Ne PAS ajouter `last_error_ts` dans l'EA : le binaire vient de passer deux audits, on ne le
rouvre pas pour de l'observabilité.

## 2. « SPECS LIVE HORS BORNES » — **VRAIE, connue, action prévue**

Confirmée dans le journal MT5 de vendredi (19:45 et 20:05). Les swaps ont réellement dérivé :

| jambe | mesuré | ancre | dérive |
|---|---|---|---|
| XAUUSD | −93,00 / −10,40 | −65,68 / −14,53 | **+42 %** sur la jambe longue |
| USDJPY | 1,63 / −26,07 | 0,96 / −20,30 | +70 % / +28 % |
| GER40 | −441,62 / −28,19 | −393,88 / −48,68 | +12 % / −42 % |

C'est l'item `spec_bounds_breach = 1` déjà au TODO (« ré-ancrer les 4 swaps », fenêtre samedi).
**L'alerte fait son travail.** Le superviseur a déjà été durci ici : il neutralise les nombres pour
que seule une jambe ou une nature **inédite** re-alerte, avec 12 h de cooldown.

⚠ **Impact réel à ne pas minimiser** : le swap de l'or est **dans le signal** de la sleeve gold
(TSMOM sur rendement total ajusté du portage). Poids actuellement nul, donc sans effet immédiat —
mais à ré-ancrer avant toute réactivation.

## 3. « brain_status stale >25h » — **FAUX POSITIF STRUCTUREL, ~47 alertes par week-end**

Le brain tourne correctement : dernière exécution `brain OK 2026-09-04`, cron `50 19 * * 1-5`.

Mais **la cron exclut le week-end** et le seuil de péremption vaut **25 h**. De vendredi 21:50 Paris
à lundi 21:50 Paris il s'écoule **72 h**. Le bloc `supervisor.py:431-437` **n'a aucune garde
week-end** ⇒ l'alerte est **mathématiquement garantie de se déclencher tout le week-end**, toutes
les 60 minutes, soit **~47 alertes chaque semaine**.

**Correctif proposé** : comparer non pas à 25 h fixes, mais à **la dernière occurrence PRÉVUE de la
cron**. Alerter seulement si le brain n'a pas tourné alors qu'il aurait dû.

## 4. Le motif commun — et il en existe un troisième cas

Les points 1 et 3 sont deux instances de la même faute : **des champs de `state.json` qui
signifient « dernière valeur connue » sont consommés comme s'ils signifiaient « valeur courante ».**

Troisième instance, non alertée mais présente : `targets_status = "OK"` avec
`targets_age_h = 62,3`. La règle de l'EA marque `STALE` au-delà de 26 h — les deux champs se
contredisent dans le même fichier. Le statut date de vendredi 22:05, dernière fois que
`TargetsValidate()` a été appelée.

⚠ **Ce n'est pas cosmétique.** Le superviseur lui-même documente que la fatigue d'alerte a déjà
coûté cher : *« celle-là même qui a coûté 38-60 séances de "LIVRE MONO" non vues »*. Une alerte qui
crie 47 fois par week-end pour rien est exactement le mécanisme qui fait rater la vraie.

**Règle proposée** : tout champ d'état consommé par une alerte doit porter **son propre horodatage**,
ou être **recalculé à la lecture**. Jamais alerter sur une valeur dont on ne sait pas si elle est
courante.

---

## Ce que je recommande

Les trois correctifs sont **Python seul** (`supervisor.py`), sans toucher à l'EA ni à la spec. À
grouper avec le ré-ancrage des swaps dans la fenêtre de samedi.

Aucun n'est urgent : **rien n'est cassé côté trading**. Le coût actuel est du bruit, mais un bruit
qui dégrade la capacité à voir un vrai incident.
