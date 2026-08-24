# PRÉ-REGISTRATION — BTCUSD comme 5e actif du pipeline `engine` (Volet C)

**Gel : 2026-07-13 · Auditeur ≠ auteur · offline.** Commit AVANT tout résultat (corrélation / triplet).

## Question (une seule, zéro degré de liberté)
BTCUSD ajouté comme **5e actif** au pipeline `engine.build_signals()` **existant**, **sans aucune
modification de la logique de signal** (mêmes lookbacks 60/120/250, carry-adj θ=0,34, book-vol 60d,
derisk 20d, equity-gate MA100, shift(1)), à **vm14** → **le triplet du book s'améliore-t-il ?**
Un seul essai. Rien à choisir → ne déflate quasiment rien.

## Contrôle d'entrée (SSH read-only, state.json VPS 2026-07-13 00:09 Paris)
`kill=0 · flat_today=0 · positions=[] · FLAT ABSENT · P1 · equity 9641.29 · vm14 · spec_sha 56fbdde78a2e`.

## Séquence gelée
1. **Faisabilité d'exécution** (peut tuer en 20 min, sources : `market_export.json` / doc FTMO / démo — **pas le terminal armé**) :
   - BTCUSD disponible sur le compte **Swing** <ACCOUNT_ID> ? contract size, min lot, step, **levier crypto effectif Swing** (les rapports supposent 1:3,33 = compte *Normal*).
   - **swap** : rapport #2 modélise −30 %/an ≈ 8,22 bps/nuit ×3 vendredi. Sur un book **swing** multi-jours = drag. Mesurer/acter, pas supposer.
   - **granularité** : min lot 0,01 BTC à ~$60-100k = ~$600-1000 notionnel = **6-10 % equity/pas** sur $10k. Le sizing cible vm14 est-il atteignable ?
2. **Corrélation au book** (jamais mesurée par les 2 rapports) — l'hypothèse à RÉFUTER :
   - corr(P&L trend BTC, P&L Nightly US100), corr(BTC, Or-trend XAU), corr(BTC, J1 USDJPY), corr(BTC, book composite).
   - **H : le trend BTC est long en bull-calme = exactement quand Nightly long US100 et Or long XAU → il SURCHARGE le facteur risk-on que le book porte déjà** (au lieu de diversifier).
   - Sleeve capitulation : entre long après flush −15 %/3j = typiquement risk-off global = book déjà en drawdown près du breaker 9650. Quantifier **P(breaker touché | entrée capitulation)** (proxy : co-mouvement risk-off le jour d'entrée).
3. Si faisabilité ET corrélation passent : porter BTC dans le sim cleanroom path-aware, triplet book vm14 avec/sans BTC.

## KILL RULES (pré-engagées, NON modifiables)
- ΔEV/campagne < **+$150** → NO-GO
- Δp(bust) > **+2 pts** → NO-GO
- **corr(BTC, book) > 0,35** → NO-GO (ce n'est pas de la diversification)
- swap swing rend le portage net négatif → NO-GO
- BTCUSD indisponible OU granularité de lot inexploitable en Swing → **NO-GO immédiat**

## Engagement
« Aucune variante de sauvetage si ça échoue. » Si NO-GO : **BTC clos définitivement** pour ce projet, écrit au
ledger, on passe à autre chose. Pas de 3e itération. Déploiement de toute façon **version-future** (EA gelé,
créneaux 17:35/15:30-16:05/21:30/22:05 Paris ; BTCUSD absent de `market_export.json` du compte armé). Aucun GO demandé.
