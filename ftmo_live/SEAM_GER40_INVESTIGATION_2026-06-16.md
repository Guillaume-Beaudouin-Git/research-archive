# Investigation seam GER40 (96.7 bps) — 2026-06-16 (LECTURE SEULE)

`targets.json` du 16/06, `audit.data.seams_bps` :
XAUUSD **7.04** | USDJPY **5.63** | US100 **30.53** | GER40 **96.66** bps.

**Verdict** : écart de **convention d'heure de clôture D1** entre deux sources de données
(panneau gelé du sim vs feed broker FTMO de l'EA), **PAS** un drift marché, **PAS** un
biais de niveau, **PAS** un décalage d'1 barre, **PAS** du bruit. **Impact sur le reconcile
= 0** (le reconcile ne lit jamais le panneau gelé). **Aucun risque de faux strike 3 jours.**
Le vrai locus est le **signal/brain** (momentum), pas le reconcile. **Rien patché.**

---

## 1. Les deux sources

| | Panneau GELÉ (sim, validation 462 cohortes) | Export EA (live) |
|---|---|---|
| Fichier | `data/ftmo_portfolio/cache/panel_px.parquet` | `market_export.json` (`d1` par jambe) |
| Producteur | build sim (06-11), 25 instruments, index **dates naïves** | EA `CopyRates(sym, PERIOD_D1, 0, 520)` à 21:45 Paris (mq5:1181) |
| Symbole GER40 | colonne `GER40` | broker `GER40.cash`, digits 2 |
| Fin de série | `frozen_end = 2026-06-05` | jusqu'au dernier D1 (~vendredi) |
| Frontière jour D1 | convention du build (cf. memory `mt5_data_provenance_2026-06` : MT5 FTMO-Demo, timestamp **EET/EEST** mal étiqueté « utc ») | frontière jour-serveur FTMO **live** (`server_minus_paris_min = 60` → EEST UTC+3) |

Le seam est calculé par `lib/marketdata.py:_seam_bps` (l.63-68) :
`max(|live/frozen − 1|)` sur les **5 dernières dates communes**.

## 2. Caractérisation (données réelles, dernières dates communes)

GER40 — écart **same-date** `live/frozen−1` :

| date | frozen | live | bps |
|---|---|---|---|
| 2026-05-19 | 24400.65 | 24311.61 | **−36.5** |
| 2026-05-20 | 24737.24 | 24754.91 | +7.1 |
| 2026-05-21 | 24606.77 | 24844.61 | **+96.7** |
| 2026-05-22 | 24888.56 | 24806.04 | −33.2 |
| 2026-05-25 | 25389.10 | 25394.94 | +2.3 |
| 2026-05-26 | 25184.89 | 25228.11 | +17.2 |

- **Signe mixte + magnitude variable** (2 → 97 bps) → **pas** un biais de niveau constant.
- Test décalé (`live[d]/frozen[d−1]`) = **203 bps max**, **pire** → **pas** un décalage d'1 barre.
- L'écart par jour = **le déplacement de GER40 entre les deux heures de clôture** ce jour-là
  (gros le 05-21 = grosse séance US ; ~nul le 05-25). C'est une **différence d'heure/convention
  de capture de la clôture D1**.

**Confirmation par le classement entre instruments** (même cause, intensité = amplitude de
mouvement entre les deux heures) :

| jambe | seam | nature |
|---|---|---|
| GER40 | 96.7 | indice, ferme tôt (Xetra) puis bouge toute la séance US → gros écart |
| US100 | 30.5 | indice US, écart moindre |
| XAUUSD | 7.0 | métal ~continu → petit |
| USDJPY | 5.6 | FX 24h → minuscule |

Indices ≫ FX/métal : signature canonique d'un écart d'heure-de-clôture, pas de bruit.

*Obs. secondaire* : les dates communes GER40/US100 s'arrêtent ~05-26/05-27 (n_common 506/491)
vs 06-05 pour XAU/JPY (514) → calendriers/couverture D1 indices aussi divergents entre sources
(holidays CFD ≠ FX). Non central ici, à creuser côté panneau.

## 3. Impact sur le reconcile = 0 (tracé)

`reconcile.py` et `lib/replay.py` **ne lisent JAMAIS** le panneau gelé / `cache/` (vérifié :
`grep FROZEN_CACHE|panel_px|read_parquet|/cache` → aucun). Le reconcile est **100 % feed-live** :
`m5_today` (M5 EA), bloc `eod` (broker), `fills.csv`, poids de `targets.json`. Le panneau gelé
n'entre **que** dans le calcul des **poids** par le brain (`build_live_cache`) — et ces poids
sont utilisés **à l'identique** côté réel (EA) ET côté modèle (replay) → ils **s'annulent**
dans Δ_signal. Le marquage (`eod_px`) est M5-live des deux côtés.

➡️ Un écart de 96.7 bps sur un notionnel GER40 ~84 k$ vaudrait ~810 $ « en principe », mais
cet écart **n'entre dans aucun des deux côtés** du reconcile → **contribution au résiduel = 0 $**.
**Il ne peut PAS déclencher un faux strike 3 jours.**

## 4. Le vrai locus : le SIGNAL (brain)

Au **raccord** panneau↔live (`frozen_end = 06-05`), le 1er rendement étendu est
`live[1er>06-05] / frozen[06-05]` au lieu de `… / live[06-05]` → il porte une **erreur ≈ le
seam au raccord** (ordre de quelques dizaines de bps, jusqu'à ~96 un jour de forte séance US),
injectée **une fois** dans l'historique de momentum 28 j de GER40 → léger biais du **poids**
GER40. Contamination réelle mais **modeste** (un rendement ~1 % dans un momentum multi-semaines),
et qui affecte le **trade réel** (donc *invisible au reconcile*, le modèle réplique le même poids).

Le brain **flague déjà** : `seam_warn` (> 30 bps, `SEAM_WARN_BPS`) → **GER40** (96.7) et **US100**
(30.5) listés ; XAU/JPY non. Le diagnostic fonctionne comme prévu.

## 5. Recommandation (sans appliquer)

1. **NE PAS élargir une tolérance reconcile pour GER40** — mauvaise couche, le reconcile est
   insensible au seam (§3). Ce serait masquer un non-problème côté reconcile.
2. **Réaligner la convention de clôture D1 du panneau gelé** sur celle du broker FTMO live
   (reconstruire les colonnes indices de `panel_px` depuis la même source / frontière jour-serveur
   EEST que l'export EA). Supprime le saut au raccord → corrige le **signal**, pas le reconcile.
3. **Interim acceptable** : accepter + documenter (ce fichier). Le reconcile n'est pas en danger ;
   la contamination signal est un rendement ~1 % isolé. `seam_warn` couvre la surveillance.
4. **Alternative légère côté signal** (si réalignement panneau coûteux) : neutraliser le rendement
   de raccord (calculer le 1er rendement étendu vs la valeur live à `frozen_end`, pas vs le panneau).
5. *Creuser* l'obs. secondaire (§2) : dates communes indices courtes — vérifier la couverture D1
   GER40/US100 du panneau gelé après `frozen_end`.

## Annexe — provenance & repro (lecture seule)
- Seam reproduit exactement (GER40 96.66) : `marketdata._seam_bps(px['GER40'], export_closes)`.
- `market_export.json` : `generated_at_paris 2026.06.15 21:45:00`, `server_minus_paris_min 60`.
- Aucune écriture : EA, FLAT, `targets.json`, état armé — **non touchés**.
