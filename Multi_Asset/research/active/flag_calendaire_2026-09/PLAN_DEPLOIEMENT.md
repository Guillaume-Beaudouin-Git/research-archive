# Plan de déploiement — saut de l'ORB les jours FOMC

**Cible : samedi 12 septembre 2026.** Premier jour d'application : **mercredi 16 septembre**
(FOMC avec projections économiques). Sinon la fenêtre suivante est le 28 octobre.

⚠ **Ce document est une PROPOSITION. Aucun fichier live n'a été modifié.**

---

## 1. Les métriques, avec et sans le changement

Book funded réellement déployé, 2 188 jours (2018-01 → 2026-06), rendements quotidiens.
67 jours FOMC, soit **3,1 % de l'échantillon** — 67 trades ORB supprimés sur 2 123.

| | jours actifs | %/an | vol | **Sharpe** | Sortino | MaxDD | WR | PF | skew | kurt | t_HAC | pire jour |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ORB actuel** | 2 123 | +3,86 % | 4,66 % | **+0,83** | +2,99 | −6,18 % | 46,2 % | 1,14 | +1,39 | 6,53 | +2,76 | −0,32 % |
| **ORB sans FOMC** | 2 056 | +4,52 % | 4,59 % | **+0,98** | +3,48 | −5,09 % | 46,8 % | 1,17 | +1,38 | 6,59 | +3,26 | −0,32 % |
| **BOOK actuel** | 2 156 | +7,08 % | 6,05 % | **+1,17** | +2,47 | −4,11 % | 48,1 % | 1,22 | +0,96 | 6,74 | +3,92 | −1,49 % |
| **BOOK sans FOMC** | 2 090 | +7,74 % | 5,99 % | **+1,29** | +2,65 | −3,96 % | 48,8 % | 1,25 | +0,94 | 6,72 | +4,29 | −1,49 % |

**Deltas** : Sharpe ORB **+0,155** (0,83 → 0,98) ; Sharpe book **+0,120** (1,17 → 1,29) ;
rendement book **+0,65 pt/an** ; MaxDD book **+0,15 pt** (moins profond).

Lecture honnête de chaque colonne :
- **Le gain est réel sur toutes les dimensions** : rendement, volatilité, Sharpe, Sortino, drawdown,
  taux de réussite, facteur de profit, t-stat. Aucune ne se dégrade.
- **Le skew ne change pas** (+1,39 → +1,38) et **le pire jour est identique** (−0,32 %) : les jours
  FOMC ne portaient pas la queue. On retire une perte *moyenne récurrente*, pas un risque extrême.
- **Le t_HAC de l'ORB passe 2,76 → 3,26**, ce qui compte pour la décision d'octobre.
- ⚠ **Réserve maintenue** : le ratio effet/MDE80 vaut 0,81 sur l'effet FOMC lui-même. Le placebo
  apparié est à p = 0,0011 et le confondant mercredi est écarté, mais l'estimation ponctuelle
  restera bruitée. **Attendre +0,65 pt/an exactement serait une erreur** ; attendre un gain positif
  de magnitude incertaine est la bonne lecture.

---

## 2. Le piège de conception à éviter

**Constat de code** : le funded ORB (`book_executor.mq5`, branche
`else if(FundedOrbOn() && width_ok && !g_flat_today)`) **ne consulte PAS `targets.json`.** Seule la
branche micro-ORB vérifie `g_targets_status`. C'est confirmé empiriquement : le lundi 31 août l'ORB
a bien pris position à 16:06 alors que les cibles du vendredi étaient forcément `BAD_ONDAY`.

⇒ **Faire passer le blocage par `targets.json` introduirait une dépendance nouvelle** du funded ORB
à un fichier qui est régulièrement invalide (chaque lundi, cibles du vendredi périmées). Deux
défauts symétriques, tous deux inacceptables :

| conception | défaut |
|---|---|
| bloquer si les cibles sont invalides | l'ORB serait coupé **tous les lundis** |
| lire un champ dans les cibles | le champ vaut 0 quand le fichier est périmé ⇒ **l'ORB tirerait quand même un jour FOMC** |

**Solution retenue : un fichier dédié, découplé du cycle quotidien du brain.**
`fomc_dates.txt` contient la **liste** des dates FOMC à venir (pas un drapeau du jour). L'EA teste
si la date du jour y figure. Le fichier n'a besoin d'être rafraîchi **qu'au changement de
calendrier**, soit une fois par an — donc jamais périmé au sens quotidien.

---

## 3. Les modifications, exactement

### 3.1 Nouveau fichier — `MQL5/Files/fomc_dates.txt`

Une date `YYYY.MM.DD` par ligne, format natif MQL5. Contenu initial (source
`data/personal_book/post_fomc_drift/data_cache/fomc_events_forward.csv`, relevé officiel Fed
2026-09-07) : `2026.09.16`, `2026.10.28`, `2026.12.09`, puis les 8 dates 2027.

### 3.2 `book_executor.mq5` — deux ajouts

**(a) Une fonction de lecture**, appelée une fois par jour au premier tick :

```cpp
bool IsFomcToday()
  {
   int h=FileOpen("fomc_dates.txt", FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE) { SetError("fomc_dates.txt ABSENT — ORB non filtre"); return false; }
   string today=TimeToString(TimeCurrent(), TIME_DATE);   // "YYYY.MM.DD" serveur
   bool hit=false;
   while(!FileIsEnding(h))
     { string l=FileReadString(h); StringTrimLeft(l); StringTrimRight(l);
       if(l==today) { hit=true; break; } }
   FileClose(h);
   return hit;
  }
```

**(b) Une condition à l'ENTRÉE uniquement** :

```cpp
else if(FundedOrbOn() && width_ok && !g_flat_today && !g_fomc_today)
```

⚠ **Ne JAMAIS gater `FundedOrbOn()` elle-même** : cette fonction sert aussi aux chemins de sortie.
La bloquer empêcherait la fermeture d'une position déjà ouverte. **On bloque l'entrée, jamais la
sortie.**

**Comportement en cas de fichier absent ou illisible : `false`, donc ORB non filtré** — l'EA revient
exactement au comportement actuel et **émet une alerte**. Fail-open assumé et signalé : un ORB qui
tire un jour FOMC coûte en moyenne 8,5 bps ; un ORB qui refuserait de tirer sur une erreur de
fichier coûterait tout l'edge.

### 3.3 `state.json` — un champ de contrôle

Ajouter `"fomc_today": 0|1` pour que la supervision et la réconciliation voient l'état sans
inspecter le fichier. Coût nul, valeur de diagnostic élevée.

### 3.4 Ce qui NE change PAS

`spec_v22.yaml`, les pins, `SPEC_SHA256`, `brain.py`, `FU_ORB_RISK`, la logique de sizing, les
sleeves overnight, les invariants de risque. **Le contrat de spec est intact** — c'est un filtre
d'entrée, pas un changement de politique de risque.

---

## 4. Ordre d'exécution — samedi 12 septembre

Rappel : le VPS `git pull` **toutes les 30 minutes**, donc **merger EST un déploiement Python**.
Ici aucun fichier Python ne change, ce qui simplifie beaucoup.

| # | étape | où |
|---|---|---|
| 1 | Geler la branche, relire le diff EA ligne à ligne | local |
| 2 | Compiler le `.ex5`, noter le hash | MetaEditor |
| 3 | **Backtest de non-régression** : rejouer 2026-08-17 → 2026-09-11 avec et sans le fichier de dates, vérifier que les fills sont **identiques** (aucun FOMC sur la période ⇒ diff attendu = zéro) | tester MT5 |
| 4 | Test positif : mettre une date de test dans le fichier, vérifier que l'ORB ne tire pas ce jour-là | tester MT5 |
| 5 | Arrêter MT5 sur le VPS | VPS |
| 6 | Déposer `fomc_dates.txt` dans `MQL5/Files/` | VPS |
| 7 | Déposer le nouveau `.ex5` | VPS |
| 8 | Relancer MT5, **vérifier qu'AlgoTrading est actif** (le changement de binaire le désactive parfois — incident connu) | VNC |
| 9 | Vérifier `state.json` : `fomc_today` présent, `targets_status`, `mode_mismatch=0` | VPS |
| 10 | Merger la branche sur `main` (documentation + calendrier source) | GitHub |
| 11 | Lundi 14, contrôle : l'ORB tire normalement (pas un jour FOMC) | VPS |
| 12 | **Mercredi 16, contrôle décisif : aucun `funded_orb_entry` dans `fills.csv`** | VPS |

## 5. Retour arrière

**Immédiat, sans recompilation** : supprimer `fomc_dates.txt` du VPS ⇒ `IsFomcToday()` renvoie
`false` ⇒ comportement actuel restauré au tick suivant, avec une alerte au journal.

**Complet** : redéposer le `.ex5` précédent, conservé sous
`archive_pre_fomc_20260912/`.

## 6. Critères d'arrêt

- Si l'étape 3 montre le moindre fill différent sur une période **sans** FOMC ⇒ **stop**, le filtre
  touche autre chose que ce qu'il devrait.
- Si le mercredi 16 l'ORB tire quand même ⇒ retour arrière immédiat et post-mortem : le format de
  date ou le fuseau du serveur ne correspond pas.
- Si `mode_mismatch` passe à 1 après déploiement ⇒ retour arrière.

## 7. La décision qui reste ouverte

Ce déploiement **ne préjuge pas** de la décision ORB d'octobre. Il l'informe : au coût mesuré de
2,11 bps s'ajoutait un défaut daté de 0,65 pt/an, désormais retiré. Le t_HAC de l'ORB passe de 2,76
à 3,26, ce qui **déplace la sleeve dans la matrice** — à re-trancher en octobre avec la mesure de
dérapage à N=30.
