# Note d'architecture — exécution du sleeve month-end (à acter, AUCUN code EA)

Créneau requis : entrée 08:00 UTC (09:00 Paris hiver / 10:00 été), sortie 11:59 UTC (12:59/13:59 Paris).
Grille EA vérifiée (`book_executor.mq5` + cleanroom `SCHED_MIN`) : actions uniquement à Paris
**09:00 / 15:30 / 16:00 / 17:35 / 21:30 / 21:45 / 22:00 / 22:05 / 22:58**. L'EA ne lit `targets.json`
qu'à ces créneaux. → La **sortie 11:59 UTC (≈13-14:00 Paris) n'a AUCUN créneau** (trou 09:00→15:30) ;
l'entrée ne s'aligne (09:00) qu'en hiver. Le sleeve est donc **NON déployable sans recompile EA**
(interdit cette session) → statut **version-future (LCAP8)**, quel que soit le résultat des tests.

Trois options (aucune retenue ici, aucune ne justifie un recompile vu le NO-GO) :
1. **Créneaux dans une future version d'EA** : ajouter 08:00/11:59 UTC à la grille + une jambe crypto au
   `targets.json`. Coût : re-spec + re-pin `spec_sha` + re-test chaîne gelée. Réservé à une release EA planifiée.
2. **Exécuteur séparé** (process/compte MT5 distinct piloté hors book) : évite de toucher l'EA armé,
   MAIS risque de collision avec le breaker/`g_flat_today` si sur le MÊME compte (une touche breaker
   `FlattenAll` fermerait aussi la jambe BTC ; un `g_flat_today` collé la bloquerait). Isolation partielle only.
3. **Compte séparé** (BTC sur un compte FTMO/broker dédié) : découple totalement du book (pas de
   contamination breaker), au prix d'un 2ᵉ frais de challenge + capital fractionné + surveillance dédiée.
