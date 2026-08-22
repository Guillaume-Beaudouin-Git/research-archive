# Dossier de vérification — Dérive overnight des indices (saisonnalité session × jour)
*But : te permettre de reproduire et de FALSIFIER le résultat de ton côté. Tout est posé pour que tu
puisses recalculer chaque chiffre et traquer une éventuelle erreur. 2026-06-03.*

---

## 0. Le résultat en une phrase (à reproduire)
Sur les indices actions, **le rendement se gagne la nuit (close→open), pas le jour (open→close)**, et
la dérive overnight est concentrée en **milieu de semaine**. Sur **NQ 2010-2026** : overnight toutes
nuits **+4,90 bps/nuit, t=4,04**, avec **IN(<2019)=+4,87 ≈ OOS(≥2019)=+4,92** et **15/17 années
positives**. Confirmé indépendamment sur **GER40**. C'est un *edge* robuste ; ce n'est PAS (tel quel)
un passe-challenge 2 mois (voir §6).

---

## 1. Définition EXACTE de la stratégie (lis le §1.1, c'est LE piège)

Pour une date `t` :
```
overnight_return[t] = open[t] / close[t-1] - 1     # close de la veille -> open du jour t
intraday_return[t]  = close[t] / open[t]   - 1     # open -> close du même jour t
```
- `open[t]`  = **premier prix de la session cash** du jour t (1er bar RTH).
- `close[t]` = **dernier prix de la session cash** du jour t (dernier bar RTH).

### 1.1 ⚠️ Mapping jour-de-semaine ↔ nuit détenue (source d'erreur n°1)
Le « jour » que je reporte est le **jour de l'OPEN** (= weekday de `t`). Donc :
- **« Mardi » (open-day) = la nuit du LUNDI** : on achète au **close de lundi**, on vend à l'**open de mardi**.
- **« Mercredi » (open-day) = la nuit du MARDI** : achat close mardi → vente open mercredi.

Les deux nuits fortes à DÉTENIR sont donc **lundi soir et mardi soir**. Si tu mappes « mardi » à
« détenir mardi soir », tu décales tout d'un jour → tu ne retrouveras pas mes chiffres. **Vérifie ce
point en premier.**

---

## 2. Chiffres à reproduire

### 2.1 NQ databento 2010-2026 (RTH), overnight par jour d'open
| open-day | nuit détenue | mean (bps) | t | IN <2019 | OOS ≥2019 |
|---|---|---:|---:|---:|---:|
| Lun | ven→lun (week-end) | +3,18 | 1,04 | +3,64 | +2,65 |
| **Mar** | **lun soir** | **+7,44** | **2,90** | +5,29 | +9,91 |
| **Mer** | **mar soir** | **+8,69** | **3,44** | +7,92 | +9,57 |
| Jeu | mer soir | +2,94 | 1,08 | +4,19 | +1,50 |
| Ven | jeu soir | +2,16 | 0,82 | +3,27 | +0,86 |
| **TOUTES** | — | **+4,90** | **4,04** | +4,87 | +4,92 |

Contraste — **intraday (open→close)** NQ : toutes = **+2,82 bps, t=1,77**, instable par jour (ex.
lundi intraday : IN −0,44 / OOS +17,5 = artefact régime). → l'edge est bien overnight, pas intraday.

### 2.2 Confirmation cross-marché — GER40 (CFD, 2022+)
| open-day | mean (bps) | t | IN | OOS |
|---|---:|---:|---:|---:|
| **Mar** | **+12,99** | **2,66** | +10,77 | +13,67 |
| Toutes | +3,65 | 1,53 | −0,73 | +4,98 |

US100 CFD (2021+) confirme aussi : mardi-open +10,28 (t=2,04, IN +6,75 / OOS +11,63).

### 2.3 Net de swap (US100.cash, capture specs)
- swap_long = **−662,4 points**, digits=2 (1 point=0,01), contract=1 → −662,4×0,01 = −6,624 prix ;
  sur ~21 500 → **−3,08 bps/nuit (1x)**. swap_short = +28,58 pts. **swap_3x_day = VENDREDI**.
- Donc nuits **lundi/mardi soir = 1x swap** :
  - Mar-open net = 7,44 − 3,08 = **+4,36 bps/nuit**
  - Mer-open net = 8,69 − 3,08 = **+5,61 bps/nuit**
  - Toutes-nuits net = 4,90 − 3,08 = +1,8 (et les vendredis en 3x la plombent → ~0). **C'est pourquoi
    la version "toutes les nuits" est marginale et la version midweek survit.**

---

## 3. Comment reproduire (méthodo exacte)

**Données :** `data/raw/NQ_1min_databento_2010-2026.parquet` (colonnes incl. `is_rth`, index temps UTC).
Filtrer `is_rth==True`, grouper par date, prendre `open=first`, `close=last`.

**Code de référence (cœur du calcul) :**
```python
import pandas as pd, numpy as np
d = pd.read_parquet("data/raw/NQ_1min_databento_2010-2026.parquet").reset_index()
d["dt"] = pd.to_datetime(d["timestamp_utc"]); d = d[d.is_rth==True]
d["date"] = d.dt.dt.normalize()
g = d.groupby("date"); o = g.open.first(); c = g.close.last()
df = pd.DataFrame({"o":o,"c":c}); df["pc"] = df.c.shift(1)        # shift(1) = veille, PAS shift(-1)
df["overnight"] = (df.o/df.pc - 1)*1e4
df["wd"] = df.index.weekday                                       # weekday de l'OPEN (cf §1.1)
print(df.groupby("wd").overnight.mean())                          # 0=Lun..4=Ven
print(df.overnight.mean(), df.overnight.mean()/(df.overnight.std()/len(df)**0.5))
```
Script autonome fourni : **`verify_overnight.py`** (tourne sur le parquet NQ **et** sur n'importe quel
CSV daily `Date,Open,Close`).

---

## 4. ✅ Checklist des sources d'erreur (ce que j'ai vérifié — re-vérifie)
1. **Mapping jour/nuit (§1.1)** — la confusion #1. open-day mardi = nuit de lundi.
2. **Look-ahead** — `close[t-1]` via `shift(1)`. Aucun prix futur utilisé. (Vérifie : pas `shift(-1)`.)
3. **Timezone** — NQ databento = vrai UTC + flag `is_rth` → pas d'ambiguïté de session. (Pour les CFD
   M1 c'est broker-EET, vérifié empiriquement ; mais pour FALSIFIER, utilise des données **daily**
   d'indice → zéro problème de fuseau, l'open/close cash sont déjà bons — cf §5.)
4. **Définition open/close** = 1er/dernier bar RTH. Sur daily, = Open/Close de la barre journalière.
5. **Swap** — −662,4 pts → −3,08 bps : confirme l'unité (point=0,01) ; et surtout **le swap réel varie
   par broker / par régime de taux** → vérifie sur TON compte (capture). 3x = vendredi à confirmer aussi.
6. **Multiple-testing** — le chiffre robuste est **TOUTES nuits (+4,90, t=4,04)**, non cherry-pické. La
   concentration midweek est un *post-hoc* mais **cross-confirmé NQ+GER40+US100** (3 marchés, même jour)
   → crédible, pas une cellule isolée. Traite +4,9 comme la borne dure, midweek comme l'amélioration.
7. **Continuité du contrat** — NQ databento est roll-adjusted ; un `is_roll_day` existe (exclure si tu
   veux être strict — impact négligeable sur l'open/close).
8. **CFD vs futures** — l'edge est le même sous-jacent ; coûts différents (futures : commission+spread,
   pas de swap ; CFD US100 : swap, pas de commission). Le net de §2.3 est pour le CFD FTMO.

---

## 5. 🔬 Test INDÉPENDANT (le plus important — hors de mon pipeline)
L'effet est si robuste qu'il apparaît sur **n'importe quelles données daily d'indice gratuites**.
Récupère QQQ ou ^NDX (yfinance), 2010-2026, et calcule :
```python
import yfinance as yf, numpy as np
df = yf.download("QQQ", start="2010-01-01")[["Open","Close"]]
df["pc"]=df.Close.shift(1)
ov=(df.Open/df.pc-1)*1e4; intr=(df.Close/df.Open-1)*1e4
print("overnight:", round(ov.mean(),2),"bps   intraday:", round(intr.mean(),2),"bps")
print("by weekday overnight:", (ov.groupby(df.index.weekday).mean()).round(2).to_dict())
```
**Attendu :** overnight nettement **positif** (~+3 à +5 bps/jour, l'essentiel du rendement total),
intraday **~plat/négatif**, et la dérive overnight plus forte en milieu de semaine. Si tu retrouves
ça, l'effet est confirmé indépendamment de mes données/codes. (C'est le résultat académique connu :
Cooper-Cliff-Gulen 2008 ; Lou-Polk-Skouras 2019 « A Tug of War ».)

---

## 6. Caveats honnêtes (ne pas survendre)
- **Edge ≠ passe-challenge.** Comme edge, c'est robuste et +EV net de swap. Comme **sprint FTMO 2 mois**,
  mon sim dit **p(<2mo) ≈ 5-10 %** : fréquence 2 nuits/sem + **queue de gap overnight** (pas de stop
  intraday) plafonnent le levier. Éventuel (sans limite de temps) ≈ 34 %. → véhicule **compte financé /
  horizon long / sleeve de book**, pas sprint.
- **Queue de gap = le vrai risque DD journalier.** Pire nuit NQ midweek ≈ −6,3 %. À levier L, une nuit
  de −x % perd L·x %. Sizer pour que la pire nuit plausible reste < 5 % (≈ levier ≤ 1,5-2x sans gate).
- **Swap = make-or-break.** Tout repose sur swap ≤ ~3 bps et 3x≠midweek. **Mesure-le sur ton compte**
  avant de conclure (comme le spread US100.cash, c'est une mesure, pas une hypothèse).
- **Régime.** L'overnight a eu des années négatives (2/17) ; sizer petit, pas all-in.

---

## 7. Fichiers
- `verify_overnight.py` — script autonome (NQ parquet + CSV daily générique).
- `code/scan.py` — scan systématique session×jour (a produit les tables §2).
- `code/overnight_sim.py` — MC FTMO 2-step sur l'overnight (a produit le §6).
*Si un de tes chiffres contredit ce document : commence par le §1.1 (mapping) et le §4.2 (shift).*
