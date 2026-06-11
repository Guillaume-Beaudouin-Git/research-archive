# BUILD EA v2.2 — contrat de spec (amendement au brief, 2026-06-10)

**Spec = `v22/spec_v22.yaml` @ 87b6cd4 (sha `56fbdde7…` (v2.2.1)). Rien n'est régénéré ni retapé ici.**
Pins baseline : `605f4a4` (contrat v2.2) + `4e1bac5` (résidus) + `87b6cd4` (gel yaml).

## Chaîne zéro-constante-manuelle (l'ancre #19 étendue au live = ancre #20)
```
config_v22.py ──make_spec_yaml.py──▶ spec_v22.yaml (sha 56fbdde7…, ancre #19)
                                          │
               brain.py.load() ◀──────────┤  (pin sha + drift-check vs config_v22 + pins commits)
                                          │
              make_spec_mqh.py ◀──────────┘
                 │            └──▶ spec_v22.sha256  → à déposer dans MQL5/Files/
                 └──▶ spec_v22.mqh (constantes EA + SPEC_SHA256 embarqué, sha 2fc65503…, ancre #20)
                          │
                EA OnInit() → SpecHashOK() : lit MQL5/Files/spec_v22.sha256,
                refuse de trader si absent/différent de l'embarqué.
```
- `brain.py` (Python, décision/réconciliation) : charge le yaml, REFUSE tout écart
  (hash, drift vs config_v22.py, pins). Test négatif vérifié : yaml altéré → SpecError.
- `make_spec_mqh.py` : émet le .mqh DEPUIS le yaml (jamais depuis le .py), déterministe
  byte-identique. Ne jamais éditer le .mqh à la main.
- L'EA n'a AUCUNE constante locale : tout #define vient du .mqh généré.

## Règles d'implémentation imposées par la spec
1. **Challenge : ORB OFF comme sleeve P&L** (`CH_ORB_RISK 0.0`). **Le compteur de jours
   EST le bloc `micro_orb_day_counter`** : 0.01 lot US100.cash, OR 15:30-16:00 CET,
   entrée premier bar post-OR (fills 16:05-16:10), sorties V2+E7 (stop côté opposé 1R,
   trail-to-BE après +1R, time-stop 22:00), **posté seulement si AUCUN autre trade
   ouvert à 21:30 CET** (flag `opened` — sémantique 605f4a4). Le backstop token
   (open/close 0.01 lot) n'est QUE le fallback no-signal, rare (50/13 068 jours sim).
2. **Funded : bloc switch du yaml**, déclenché AU FUNDING, même événement que vm14→1.0 :
   vm 14→1.0, on_w 0.6→0.35, ORB ON full spec (0.25% taper), micro-ORB OFF,
   pace/glide/abandon OFF, retraits wd14.
3. **ORB_RT_BPS lu du yaml** (`era` par défaut). **Aucun ré-ancrage avant le verdict
   N=60 du 2026-06-15.** Au verdict : éditer config_v22.py → régénérer yaml (nouveau
   sha → nouveau pin → régénérer mqh → re-déposer spec_v22.sha256) → re-run section
   funded seule (ancres #4/#5/#18). La branche kill est RETIRÉE (AMENDEMENT_RAPPORT_MESURE_s9).
4. Horaires : la spec est en **CET** ; le serveur FTMO est EET (CET+1) — le mapping se
   fait par input EA (`InpServerTZOffset`), JAMAIS en éditant les constantes.

## Vérifications
- `python3 brain.py --check` → spec OK + pins présents.
- `python3 make_spec_mqh.py` ×2 → sha mqh identique (`2fc65503…`).
- EA : compiler avec spec_v22.mqh ; OnInit doit logger `SPEC OK v2.2.1 sha 56fbdde78a2e…`.
