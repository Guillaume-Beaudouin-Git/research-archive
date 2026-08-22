# RUNBOOK — mesure de spread FTMO sur compte DÉMO (EA v2.9)

> # ⛔ OBSOLÈTE — NE PAS SUIVRE (2026-08-17)
>
> **Le compte démo n'est plus nécessaire.** Le compte funded est arrivé le 2026-08-17 et il est
> le **bon** lieu de mesure par définition (L33) ; un serveur démo n'est pas garanti être le même
> monde de cotation.
>
> Le seul rôle qui restait à la démo — valider le patch v2.9 avant qu'il ne touche de l'argent
> réel — est mieux rempli par le **compte de Phase 2 (<ACCOUNT_ID>)**, qui est **toujours authentifié
> sur FTMO-Server2 avec les cotations vivantes** mais dont le serveur a désactivé le trading
> (`trading has been disabled - disabled on server`). Cotations pour mesurer, ordres impossibles :
> banc d'essai parfait, à coût nul.
>
> ⚠ Une contrainte de ce fichier est CADUQUE et dangereuse si suivie : « déploiement SAMEDI
> uniquement ». Elle protège un compte armé ; elle ne s'appliquait pas le 2026-08-17.
>
> **Procédure en vigueur** : `AUDIT_BASCULE_FUNDED_2026-08-17.md` §6 (checklist opérateur).
> Ce fichier est conservé pour la partie technique (commandes de compilation headless wine,
> chemin VNC, garanties de non-régression du patch), qui reste exacte.

**À exécuter pas à pas.** Chaque phase a un critère de sortie explicite. Si un critère échoue,
on s'arrête et on diagnostique — on n'enchaîne pas.

**Fenêtre favorable** : P1 et P2 sont fermés, le compte funded n'est pas encore livré ⇒ le
terminal ne pilote **aucun compte réel**. La règle « déploiement samedi uniquement » protège un
compte armé ; elle ne s'applique pas ici. C'est le meilleur moment pour toucher au binaire.

**Ce que ce runbook obtient / n'obtient pas** :

| | |
|---|---|
| ✅ profil de spread FTMO natif, tick-level, aux deux horloges | le logger seul suffit |
| ✅ validation de non-régression du patch v2.9 | le but même de la démo |
| ❌ **dérapage au-delà de l'ask** | **impossible sur démo** — les fills démo sont synthétiques, remplis au prix coté par construction. Seul le compte funded le donnera, à ~6 fills/mois. |

---

## Phase 0 — préparatifs (AVANT d'avoir les identifiants démo)

Trois pièges lus dans `OnInit()` (`book_executor.mq5:1663-1696`) qu'il faut désamorcer d'abord.

### 0.1 ⚠ Archiver `ea_state.json` — À FAIRE EN PREMIER

`OnInit` appelle `LoadState()`. Si `ea_state.json` contient encore l'ancre P2 (**11 006**), l'EA
démo en hérite ; et surtout il va **l'écraser avec les données démo**. Or ce fichier est déjà
classé sécurité-critique pour la bascule funded.

```bash
ssh -o ControlMaster=auto -o ControlPath=/tmp/cc-ftmo-%r@%h:%p -o ControlPersist=300 \
    -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP>
```

Puis, sur le VPS :

```bash
cd "$HOME/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal/MQL5/Files"
cp -a ea_state.json  "ea_state.json.p2_$(date +%Y%m%d)"      # archive de l'ancre P2
cp -a fills.csv      "fills.csv.p2_$(date +%Y%m%d)"          # le ledger de fills réels
ls -la ea_state.json* fills.csv* FLAT spec_v22.sha256 2>&1
```

**Critère de sortie** : les deux archives existent, et `spec_v22.sha256` est présent (sinon
l'EA refusera d'initialiser, cf. 0.3).

### 0.2 ⚠ Pré-déposer le kill-file `FLAT`

L'EA doit tourner **désarmé** sur la démo. Le patch échantillonne quand même — c'est
exactement pourquoi l'appel est placé avant le test du kill-file.

```bash
touch "$HOME/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal/MQL5/Files/FLAT"
```

**Critère de sortie** : le fichier existe **avant** tout attachement d'EA.

### 0.3 Les trois causes d'`INIT_FAILED` à connaître d'avance

| cause | garde | parade |
|---|---|---|
| `spec_v22.sha256` absent ou ≠ `SPEC_SHA256` | `SpecHashOK()` | ne pas y toucher ; il est déjà en place |
| `InpAttemptStart == 0` avec `InpPhase != 3` | ligne 1671 | mettre la date du jour |
| **un des 4 symboles introuvable** | `SymbolSelect()` ligne 1678 | ⚠ voir 3.3 — les suffixes du serveur démo peuvent différer |

Défauts attendus : `XAUUSD`, `USDJPY`, `MICRO_ORB_SYMBOL` (mqh), `GER40.cash`.

---

## Phase 1 — compiler (headless, aucun GUI)

La compilation se fait sous wine sur le VPS. **Chemin sans espaces obligatoire** — le quoting
wine casse sur « Program Files ».

Depuis le Mac :

```bash
cd <HOME>/Desktop/Algo_claude
scp -i ~/.ssh/hetzner_algo_claude \
    ftmo_live/mt5/book_executor.mq5 ftmo_live/mt5/spec_v22.mqh \
    algo@<VPS_IP>:~/.wine/drive_c/build/
```

Puis sur le VPS :

```bash
export WINEPREFIX=$HOME/.wine DISPLAY=:1 WINEDEBUG=-all
cd "$HOME/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal"
wine ./MetaEditor64.exe /compile:C:\\build\\book_executor.mq5 /log
iconv -f UTF-16LE -t UTF-8 "$HOME/.wine/drive_c/build/book_executor.log" | tail -5
```

**Critère de sortie** : `Result: 0 errors, 0 warnings`. Un seul warning ⇒ **STOP**, me le
remonter. Garder ce log, il devient `mt5/build_2026-08-<jj>_v29.log`.

---

## Phase 2 — déployer le binaire

```bash
EXP="$HOME/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal/MQL5/Experts/ftmo_live"
cp -a "$EXP/book_executor.ex5" "$EXP/book_executor.ex5.v28_$(date +%Y%m%d)"   # rollback
cp "$HOME/.wine/drive_c/build/book_executor.ex5" "$EXP/book_executor.ex5"
sha256sum "$EXP/book_executor.ex5"
```

**Pas de re-dépôt de `spec_v22.sha256`** : `spec_v22.mqh` n'est pas modifié, le pin
`d8d3dcb1…` reste valide, aucun ré-gel de spec.

**Rollback** : recopier `book_executor.ex5.v28_<date>`. C'est tout.

---

## Phase 3 — connecter le compte démo (VNC)

### 3.1 Ouvrir le tunnel — depuis le Mac

```bash
ssh -i ~/.ssh/hetzner_algo_claude -L 5900:localhost:5900 algo@<VPS_IP>
```

Laisser ce terminal **ouvert**. x11vnc écoute en `-localhost` : sans le tunnel, rien.

### 3.2 Récupérer le mot de passe VNC et ouvrir le client

Le mot de passe est celui de `start_mt5.sh` sur le VPS (variable `VNC_PASS`, ou en dur dans la
version historique `/home/algo/start_mt5.sh`) :

```bash
grep -i "vnc" /home/algo/start_mt5.sh /home/algo/.env 2>/dev/null
pgrep -a x11vnc          # confirme que x11vnc tourne, et sur quel display
```

Puis depuis le Mac :

```bash
open vnc://localhost:5900
```

*(ou Finder → Aller → Se connecter au serveur → `vnc://localhost:5900`)*

Si rien ne répond : x11vnc est lancé par `start_mt5.sh`, donc par la session `screen mt5`.
Vérifier `screen -ls | grep mt5` et `pgrep -f '[t]erminal64'`. Le display est `:1` dans la
version versionnée, `:99` dans une doc plus ancienne — `pgrep -a x11vnc` tranche.

### 3.3 Se connecter et RELEVER LE SERVEUR

Dans MT5 : **File → Login to Trade Account**, saisir les identifiants démo.

Trois relevés obligatoires, dans l'ordre :

1. **Le nom du serveur**, au Journal (`authorized on FTMO-…`) — à noter ici :
   `serveur démo = ________________`
   Vérification côté shell :
   ```bash
   iconv -f UTF-16LE -t UTF-8 \
     "$HOME/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal/logs/$(date +%Y%m%d).log" \
     | grep -i authoriz
   ```
   ⚠ **C'est le relevé le plus important du runbook.** Si le serveur démo n'est pas le même
   monde que le futur serveur funded, la mesure de spread devra être re-validée par
   recoupement, pas prise pour argent comptant. On aura fait le tour du problème pour rien
   sinon.

2. **Les suffixes de symboles** dans le Market Watch : `US100.cash` ? `GER40.cash` ? `XAUUSD` ?
   Un seul symbole introuvable ⇒ `INIT_FAILED`. Si un suffixe diffère, corriger **l'input de
   l'EA** (`InpSymGER40`, `InpSymUS100`), **jamais les constantes du mqh**.

3. **Le décalage horaire** : dans `state.json`, `ts_server − ts_paris` doit valoir **exactement
   +60 min**. Sinon corriger `InpServerTZOffsetMin`, jamais les constantes.

---

## Phase 4 — attacher l'EA, désarmé

Vérifier que `FLAT` est bien en place (phase 0.2) **avant** d'attacher.

Glisser `book_executor` sur un graphe (ex. `US100.cash` M5). Inputs :

| input | valeur |
|---|---|
| `InpPhase` | `1` |
| `InpAttemptStart` | **la date du jour** (0 ⇒ `INIT_FAILED`) |
| `InpServerTZOffsetMin` | `60` (à confirmer, cf. 3.3) |
| symboles | ajuster seulement si le Market Watch diffère |

**AutoTrading ON.** ⚠ Un changement de compte ou un rechargement de profil le repasse
silencieusement à OFF (`ret=10027` déjà vécu). Le vérifier à l'œil dans la barre d'outils.

**Critère de sortie** — au log Experts :
- `SPEC OK v2.2.2 sha 3e7626f6d3fd…`
- 4 lignes `UPU <sym>: …` toutes avec `usd_per_unit > 0`
- `book_executor v2.2 INIT — phase 1…`
- `INIT REFUSÉ` ⇒ **STOP** (cf. tableau 0.3)

---

## Phase 5 — non-régression, ≥30 min EN SÉANCE

C'est l'étape qui autorise ou interdit tout le reste. **Aucune de ces vérifications n'est
optionnelle.**

```bash
cd "$HOME/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal/MQL5/Files"
head -3 spread_log_$(date +%Y%m).csv
wc -l spread_log_$(date +%Y%m).csv
head -1 fills.csv                      # DOIT faire 16 colonnes, inchangé
python3 -c "import json;d=json.load(open('state.json'));print(d.get('heartbeat_epoch'),d.get('kill'),d.get('mode_mismatch'))"
```

| # | vérification | attendu |
|---|---|---|
| 1 | `spread_log_YYYYMM.csv` existe, en-tête correct | 7 colonnes |
| 2 | ~1 ligne/minute/jambe cotée, **aucune minute en double** | la garde `last_min` |
| 3 | `spread_bps` plausible | **US100 ≈ 0.4-1.1 bps** hors ouverture |
| 4 | `bid`/`ask` non nuls, `ask ≥ bid` | garde de sanité |
| 5 | **`fills.csv` : 16 colonnes, inchangé** | aucun schéma touché |
| 6 | `state.json` : `heartbeat_epoch` **avance à la seconde** | le logger ne ralentit pas `OnTimer` |
| 7 | `kill = 1` | l'EA est bien désarmé |
| 8 | **zéro ordre** — aucune ligne neuve dans `fills.csv` | le patch ne trade pas |

**Un seul échec ⇒ rollback (phase 2) et diagnostic.**

⚠ Vérification 3 : hors séance US, les jambes seront filtrées par la garde de fraîcheur
(120 s). Un fichier vide un dimanche est **normal**, pas une panne. Faire ce test **en séance**.

---

## Phase 6 — récolte

### J+3 — contrôle de sanité précoce

Ne pas attendre deux semaines pour découvrir un problème de format.

```bash
ssh -o ControlMaster=auto -o ControlPath=/tmp/cc-ftmo-%r@%h:%p -o ControlPersist=300 \
    -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP> \
    'cat "/home/algo/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal/MQL5/Files/spread_log_'$(date +%Y%m)'.csv"' \
  > /tmp/spread_j3.csv
wc -l /tmp/spread_j3.csv
```

Attendu : quelques milliers de lignes, les 4 jambes présentes, une couverture horaire continue.

### J+14 — la mesure

Même commande. Ce qu'on en tire :
- le spread médian et le **p95** dans la fenêtre ORB, **aux deux horloges** (serveur et Paris,
  toutes deux estampillées ⇒ la conversion vers ET est vérifiable au lieu d'être supposée) ;
- le profil horaire complet des 4 jambes ;
- la comparaison au `0.95-1.06 bps RT` de `mt5_us100_spread_corrected_et_bucket.csv`, dont la
  « correction » de fuseau est un décalage de **3 h exactement** que rien ne justifie
  (EET/EEST ↔ ET valent 6 ou 7 h). **C'est ce runbook qui tranche ce point.**

⚠ **Ce fichier ne va JAMAIS dans git.** ~2 Mo/semaine, rotation mensuelle par construction.
Purger les mois déjà tirés.

---

## Phase 7 — nettoyage AVANT la bascule funded

À faire au moment où FTMO livre les identifiants funded, **sans exception** :

1. **`rm ea_state.json`** — sécurité-critique, et **le passage en démo en rajoute une couche** :
   le fichier contiendra désormais l'ancre du compte démo. Une ancre héritée sur un compte à
   10 000 = breach immédiat.
2. Mettre de côté les lignes `fills.csv` de la période démo (elles polluent le ledger de fills
   réels et l'analyse de coût). Les archives de la phase 0.1 servent de référence.
3. `InpPhase = 3`, `InpAttemptStart` manuel.
4. **`FU_ORB_RISK = 0`** — l'ORB ne s'allume pas. Le spread ne sera mesuré qu'à partir de la
   phase 6, et le dérapage pas avant ~10 mois.
5. Ré-ancrer le swap GER40 (`spec_bounds_breach: 1` actif, ancre périmée de +13.5 %).
6. Vérifier AutoTrading rallumé (VNC).

---

## Ce que ce runbook ne réglera pas

Deux limites structurelles, à garder en tête pour ne pas surinterpréter le résultat :

- **La couverture historique s'arrête à 2022.** `mt5_us100_bars_per_day_by_year.csv` montre
  **1 barre/jour en 2018, 2019, 2020**, partiel en 2021, 1 365/jour à partir de 2022. Aucune
  mesure FTMO-native ne peut couvrir 2018-2021. Or c'est précisément la période dont dépend le
  verdict « 2018-2026 passe ». **La période mesurable est celle où l'ORB a l'air bon**
  (t 3.72 sur 2022-2026 contre 0.62 / 0.10 / 1.05 avant) — circularité à nommer, pas à ignorer.
- **La concentration de régime du gross ORB**, qui est *avant tout coût*. Aucune mesure de frais
  n'y répond. Il faudra un test forward pré-enregistré, avec date de départ justifiée sur le
  régime de coût et fixée avant de regarder la performance.
