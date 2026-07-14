# PRÉ-REGISTRATION — re-stamp des targets le lundi (`monday_restamp.py`)

> Figé 2026-06-29 AVANT implémentation. Compte PAYÉ armé FTMO-Server3 (<ACCOUNT_ID>),
> position USDJPY ouverte. EA `book_executor` GELÉ. `brain.py` NON modifié.
> Composant NOUVEAU et ADDITIF. Ce contrat lie l'implémentation : toute divergence
> = invalidation, re-pré-registration requise.

## 0. AMENDEMENT 2026-07-13 — re-pré-registration après audit indépendant (bloquant résolu)

> L'audit indépendant de l'étape 4 (session fraîche, auteur ≠ auditeur, 2026-07-13) a **REJETÉ**
> la v1 pour UN chemin bloquant, né APRÈS le gel de cette pré-reg (le gate J1 `lib/j1_gate.py`
> a été ratifié 2026-07-03, postérieur au gel 2026-06-29 — cette pré-reg ne POUVAIT pas l'analyser) :
>
> **Défaite du gate J1 le lundi où le brain échoue.** Le re-stamp rend les targets de vendredi
> fraîches pour TOUTE la journée du lundi — pas seulement le créneau GER40 17h35, mais AUSSI le
> rebalance 22h05 (même gate `age_h>26.0`, `book_executor.mq5:874` ; un seul horodatage gouverne
> les deux). Or le gate J1 est **100% côté brain** (le brain zéro `ea_w_usdjpy` quand USD/JPY est
> en zone d'intervention ; aucune protection J1 côté EA — grep confirmé). Si le brain n'écrit PAS
> de targets fraîches à 21h50 (crash / lenteur / export vieux / lundi férié), alors le rebalance
> 22h05 (`:1071 tgt[1]=JD("ea_w_usdjpy")*sc*eq`, gaté seulement par `TargetsValidate` `:1058`)
> traderait le poids J1 de **vendredi** — reflétant l'état de gate de vendredi, pas de lundi.
> **Sans** le re-stamp, la staleness bloquait ce rebalance (`:1058-1062` → « gestion seule »).
> Le breaker M5 a déjà été battu par le flash d'intervention (« FTMO continuous liq beat discrete
> M5 breaker », compte <ACCOUNT_ID>). Conséquence = **exactement le profil des 2 breaches USDJPY**
> (~16× long dans la zone), sur un compte à ~$641 du floor. Conjonction déclenchante : gate
> vendredi OFF (poids ≠ 0) + USD/JPY entre en zone ≥160 sur le week-end + brain muet lundi 21h50
> + EA vivant à 22h05. Contrôle : si gate vendredi déjà ON (`ea_w_usdjpy=0`), le 0 est préservé →
> 22h05 trade 0 → sûr.
>
> **Correctif (ce document RE-GÈLE le contrat) — fail-closed complet sur les poids data-dépendants :**
> le re-stamp met **`ea_w_usdjpy = 0.0` ET `ea_w_xauusd = 0.0`** — doctrine du gate J1 (« donnée
> illisible → suspend »), **étendue le 2026-07-14 à l'or** : un lundi où le brain est mort, on ne
> fait confiance à AUCUN poids data-dépendant (les deux SEULS de `targets.json` sont `ea_w_usdjpy`
> et `ea_w_xauusd`). **Inerte au cas normal** (le brain écrase la totalité des targets à 21h50,
> AVANT toute consommation de poids ; entre 13h et 21h50 aucun créneau ne lit `ea_w_*` — les deux
> poids ne sont lus qu'à 22h05, `:1070-1071` — cf. §6). **Protecteur au cas dégradé** (22h05 garde
> J1 ET l'or à plat ; seules les jambes calendaires `on_w` — US100 `:1072`, GER40 — sont tradées).
> N'affecte PAS le fix GER40 (leg 3 = `on_w`, indépendant des poids data) ni `ea_on_w` (poids
> calendaire US100/GER40, **jamais touché**). **Coût de l'extension or ≈ 0** : P(brain muet lundi) ×
> P(or≠0) ≈ 0,6–2 jours-or/an, exposition symétrique ⇒ **P&L espéré nul à toute fréquence** (+ coût
> de transaction négligeable) ; l'or se ré-établit au prochain run brain. Le bloc `restamp` trace
> `source_w_usdjpy`, `source_w_xauusd` + `failclosed=true`. Le bloc `audit` (dont `audit.j1_gate`
> de vendredi) reste copié verbatim (non muté). **Re-audit indépendant requis avant tout
> déploiement** (étape 4-bis).

## 1. Problème (diagnostiqué, lecture seule)

Le sim audité (`cleanroom/engine.py:142,361`) fait entrer le GER40 **chaque lundi et mardi**
(`ON = dayofweek ∈ {0,1}`), sans gate de staleness. Le live le skippe **tous les lundis** :

- `brain.py` (cron `50 19 * * 1-5`) ne tourne pas le week-end → les dernières targets datent
  de **vendredi 21h50 Paris**.
- L'EA n'écrit `market_export.json` qu'à **21h45 Paris** (`Do2145Export`, grille
  `book_executor.mq5:1514`) → **aucun export frais entre vendredi 21h45 et lundi 21h45**, donc
  `brain.py` ne PEUT pas régénérer (gate `marketdata.load_export` : `âge > 6h` → refuse d'écrire).
- Au créneau GER40 **17h35 Paris** (`Do1735`, grille `:1512`), les targets de vendredi ont
  ~67h → gate EA `age_h > 26.0` (`book_executor.mq5:870`) → `g_targets_status="STALE"` →
  `Do1735` skippe (`:993-994`).

La **donnée est correcte** : le close vendredi = le vrai T-1 d'un lundi (pas de barre
week-end ; le sim lui-même n'a que la barre vendredi). Et le GER40 17h35 **n'utilise aucun
poids data** : `tgt[3]=OnWEff()*Scale(eq)*eq` (`:1001`) = constante `on_w` × gouverneur EA ×
calendrier. Seuls l'horodatage figé (`ea_generated_at_paris`) et le flag calendaire
(`ea_on_day=0` le vendredi) déclenchent le rejet.

## 2. Objectif

Le lundi, AVANT 17h35 Paris, réécrire `targets.json` en réutilisant les targets de vendredi,
en ne modifiant QUE les champs nécessaires pour que l'EA voie `targets_status=OK` au créneau
GER40 — pour reconverger le live vers le sim audité. Fail-safe : en cas de doute, **ne rien
écrire** (un GER40 skippé > un targets corrompu sur compte armé).

## 3. Champs réécrits — liste EXHAUSTIVE et figée

| Champ | Avant (vendredi) | Après (lundi) | Pourquoi |
|---|---|---|---|
| `ea_generated_at_paris` | `2026.06.26 21:50:03` | `now_paris()` (lundi) | gate EA `age_h>26` (`:870`) — SEUL but du re-stamp |
| `ea_valid_for_date` | `2026-06-26` | date du lundi | cohérence audit (NON gaté par l'EA — vérifié `:828-895`, aucune lecture `valid_for` côté EA) |
| `ea_on_day` | `0` | `1` | gate EA `on_file != IsONDay()` → `BAD_ONDAY` (`:872`). Lundi EST un jour ON. Valeur **calendaire-déterministe** (`dayofweek ∈ {0,1}`), identique à ce que `brain.py` écrirait |
| `ea_w_usdjpy` | poids vendredi (ex. `1.21`) | `0.0` | **fail-closed J1** (amendement §0, audit 2026-07-13) : sinon, sur un lundi où le brain échoue, le rebalance 22h05 (`:1071`) traderait ce poids sous l'état de gate de vendredi (~16× USD/JPY en zone). **Inerte au cas normal** (brain écrase 21h50) ; **protecteur** au cas dégradé. Si déjà `0.0` → inchangé |
| `ea_w_xauusd` | poids vendredi (ex. `0.83`) | `0.0` | **fail-closed or** (extension §0, 2026-07-14) : même principe — brain mort ⇒ aucun poids data-dépendant tradé à l'aveugle. Lu seulement à 22h05 (`:1070`). Coût espéré ≈ 0 (§0). Si déjà `0.0` → inchangé |

**Champ additif (audit, hors `ea_*`, ignoré par l'EA) :** `restamp` (bloc) = `{source_generated_at,
source_valid_for_date, source_w_usdjpy, source_w_xauusd, failclosed, restamp_ts, reason}` pour traçabilité.

## 4. Champs JAMAIS touchés

`ea_spec_sha256`, `ea_vm`, `ea_on_w`, `ea_orb_risk`,
`ea_micro_orb`, `ea_breaker`, `ea_taper`, `ea_glide`, `ea_pace`, `ea_margin_cap`, `schema`,
et tout le bloc `audit` existant — dont `audit.j1_gate` de vendredi — (copié verbatim, non muté).
`ea_on_w` (poids calendaire des jambes ON US100/GER40) reste celui de vendredi : c'est une constante
calendaire, PAS un poids data-dépendant, et c'est le levier même du fix GER40 — le toucher casserait
l'objectif.

> **NB amendement §0 (option 2, 2026-07-14) :** les DEUX poids data-dépendants `ea_w_usdjpy` ET
> `ea_w_xauusd` **ne font PLUS partie** de cette liste — ils sont zéro-fail-closed (§3). Parmi les
> poids, seul `ea_on_w` (calendaire) reste verbatim.

## 5. Conditions de déclenchement (sinon NO-OP, exit 0)

Le script s'exécute mais **ne réécrit que si TOUTES** ces conditions sont vraies :

1. **Jour = lundi** (Paris). Tout autre jour → no-op (garde-fou si la cron tire un mauvais jour).
2. **Lundi est un jour ON** (`dayofweek ∈ {0,1}` — toujours vrai un lundi ; recalculé, pas codé en dur).
3. `targets.json` source **présent, parsable, schema == `ftmo_live.targets.v1`**.
4. `targets["ea_spec_sha256"] == spec.spec_sha256()` (loader épinglé). **Mismatch → REFUS**
   (ne pas masquer une dérive de spec réelle).
5. `targets["ea_phase_hint"]` cohérent avec la phase de `state.json` si lisible. **Mismatch →
   REFUS** (une transition de phase est impossible sur un week-end sans jour tradé ; un écart =
   anomalie).
6. **Targets actuellement STALE pour le créneau** : âge projeté à 17h35 Paris du jour `> 26h`,
   OU plus simplement âge courant `> 26h`. Si déjà frais (< 26h, ex. brain relancé manuellement)
   → no-op (rien à corriger).
7. `ea_valid_for_date` source = **le dernier jour ouvré avant ce lundi** (vendredi attendu ;
   tolérance : J-3 à J-1 calendaires). Plus ancien → **REFUS** (brain muet depuis longtemps =
   vrai problème, ne pas papier-mâcher).

Toute exception non prévue (I/O, parse, env manquant) → log + exit 0 **sans écrire**.

## 6. Sûreté — aucune target-weight consommée avant l'écrasement brain (preuve)

Sites de lecture targets de l'EA (`grep TargetsRead|TargetsValidate`, `book_executor.mq5`) :

| Action | Heure Paris | Lit les poids `ea_w_*` ? | Statut |
|---|---|---|---|
| `Do1600Arm` (`:940`) | 16:00 | non | jour ON → micro non armé (`:941 if(IsONDay()…) skip`) |
| `Do1735` (`:993`) | 17:35 | **non** (`on_w`, `:1001`) | **la cible du fix** |
| `Do2130Backstop` (`:1010`) | 21:30 | non (micro fixe) | n'appelle pas `TargetsValidate` |
| `Do2205Rebalance` (`:1055`) | 22:05 | **oui** (`:1071`) | **APRÈS** le brain 21h50 → lit normalement les targets FRAÎCHES du lundi. Cas dégradé (brain muet) traité par le fail-closed J1+or §0 |
| `WriteState` (`:1297`) | continu | non (lecture âge, no-trade) | read-only |

→ Entre le re-stamp (~13h UTC) et le brain (19h50 UTC = 21h50 Paris), la **seule** action de
trade qui lit les targets est `Do1735` (GER40, `on_w`, pas de poids). Au cas **normal**, le
rebalance XAU/JPY (22h05) lit les targets fraîches du brain → poids re-stampés jamais tradés.

**Cas dégradé (brain muet à 21h50, corrigé par l'amendement §0) :** le re-stamp rendant les
targets fraîches toute la journée, 22h05 n'est plus bloqué par la staleness. Le fix zéro
`ea_w_usdjpy` ET `ea_w_xauusd` → 22h05 garde **J1 ET l'or à plat** ; seules les jambes calendaires
`on_w` (US100 leg2 `:1072`, GER40) sont tradées. **Aucun poids data-dépendant n'est jamais tradé à
l'aveugle** sur un lundi de panne du brain. Rare et loggé.

## 7. Écriture & concurrence

- Écriture **atomique** via `statefiles.atomic_write_json` (tmp+rename, même fs) — identique au
  brain ; l'EA ne lit jamais un fichier partiel.
- Re-stamp à ~13h UTC : le 1er `TargetsRead` EA du jour (`Do1600Arm` 16h Paris = 14h UTC) est
  postérieur → pas de lecture pendant l'écriture.
- Idempotent : si relancé, condition §5.6 (déjà frais) → no-op.
- Gate EA 26h **INTACT** : le script le satisfait (timestamp frais), ne le contourne pas
  côté EA.

## 8. Heure cron (proposée à l'étape 5, justifiée ici)

`0 13 * * 1` UTC (lundi 13h00 UTC). GER40 17h35 Paris = **15h35 UTC (été)** / **16h35 UTC
(hiver)**. 13h UTC est avant les deux (marge ≥ 2h35) → **DST-safe sans seconde ligne**.
Aucune dépendance à `market_export` (le script réutilise targets.json, toujours présent) → pas
de contrainte de fraîcheur export. Note seam DST 25/10/2026 : ligne inchangée (couvre été+hiver).

## 9. Implémentation — contraintes

- Chemins via `statefiles.mt5_files_dir()` (env `FTMO_LIVE_MT5_FILES`), zéro hardcode.
- Réutilise `statefiles` (read_json, atomic_write_json, now_paris, fmt_ts, parse_ts,
  targets_age_h) + `spec.spec_sha256` ; ne réimplémente pas.
- Pas de secret. Log dédié (`logs/ftmo_monday_restamp.log`) : action + raison, ou raison du no-op.
- `--dry-run` : affiche le targets.json AVANT/APRÈS, **n'écrit pas** (pour test hors compte armé).
- Encodage : écriture via le helper existant (json.dump UTF-8) ; l'EA lit tolérant (cp1252
  fallback, `read_text_tolerant`).

## 10. Plan de test (étape 3, hors compte armé)

Sur une **copie** de la vraie `targets.json` vendredi (fixture), `--dry-run` :
1. Lundi simulé, targets STALE → produit OK : timestamp frais, `ea_on_day` 0→1, poids/sha
   IDENTIQUES. Diff = uniquement les 3 champs §3 (+ bloc `restamp`).
2. Fail-safe : sha mismatch → REFUS ; targets absentes → REFUS ; mauvais jour → no-op ;
   valid_for_date trop ancien → REFUS ; déjà frais → no-op.
3. Diff AVANT/APRÈS montré.

## 11. Audit (étape 4) — auteur ≠ auditeur

- **v1 (2026-07-13) : REJETÉ** en session fraîche indépendante — un chemin bloquant (défaite du
  gate J1 le lundi où le brain échoue). Détail + correctif : §0.
- **v2 (post-correctif) : re-audit indépendant OBLIGATOIRE avant déploiement.** Vérifie : ne
  touche que les champs §3 (désormais 5 : les 3 + `ea_w_usdjpy=0` + `ea_w_xauusd=0`),
  `ea_on_w`/`audit`/sha/mode copiés verbatim, fail-safe corrects (§5), zéro hardcode, zéro effet de
  bord EA/état, et surtout que le fail-closed data-poids est **inerte au cas normal** et
  **protecteur au cas dégradé** (§0/§6). v2 APPROUVÉ (J1-seul) 2026-07-13 ; extension or
  (option 2) 2026-07-14 → re-confirmation indépendante légère.

## 12. Hors-périmètre / décisions différées

- Le **mardi** n'a pas besoin du fix (brain a tourné lundi soir) → cron lundi uniquement.
- Ne corrige PAS le gate export 6h du brain (hors périmètre, toucherait brain.py).
- Ne réactive PAS le GER40 si le compte est en breach/FLAT (l'EA gère via `g_flat_today` ;
  le re-stamp ne force rien — `Do1735` re-teste `g_flat_today` `:992`).
