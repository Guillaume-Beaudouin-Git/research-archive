# Calendrier FOMC prospectif 2026-2027

**Créé 2026-09-07.** Comble un manque révélé par le checkup du jour : le ledger
`fomc_events.csv` s'arrête au **2026-04-29** et le calendrier économique du dépôt au
**2026-06-07**. Un flag calendaire qui ne connaît pas les dates futures ne sert à rien en live.

**Source** : https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (relevé 2026-09-07).

**Convention** : la date portée est le **second jour** de chaque réunion, c'est-à-dire le jour de
l'annonce (14:00 ET) — même convention que `fomc_events.csv`, dont les entrées historiques sont les
jours de décision.

⚠ **Avertissement de la Fed, repris verbatim de la page** : *« Each meeting date is tentative until
confirmed at the meeting immediately preceding it. »* Les dates lointaines peuvent bouger ; à
re-vérifier avant tout usage engageant, en particulier au-delà de 2026.

`SEP` = réunion accompagnée d'un *Summary of Economic Projections* (impact généralement plus fort).
