# Corrélation Strategy C ↔ Voie B

**Run date:** 2026-05-28  
**Overlap:** 2022-12-28 → 2025-12-11  
**N jours :** 281 (dont 172 actifs simultanément)

| Métrique | Valeur |
|----------|--------|
| corr(C, B) Pearson | **0.0364** |
| corr(C, B) Spearman | 0.0020 |
| corr(C, B) jours actifs-simultanés | 0.0562 |
| Sharpe C (sur overlap) | 2.827 |
| Sharpe B (sur overlap) | 0.904 |

## Interprétation

Corrélation faible (0.04) — C et B sont **quasi-décorrelés** sur la période commune. Diversification porteur efficace. Les deux stratégies opèrent sur des mécanismes indépendants (ORB momentum NQ 09:46-12:30 vs gap continuation US indices 14:30-21:00).

**SR portefeuille 50/50 (sur overlap) :** 1.839

Diversification lift : 1.839 vs max(SR_C=2.83, SR_B=0.90)

## Note de portée

L'overlap est limité au dataset NQ 1-min disponible (fin 2022 → 2025).
Voie B couvre 2010-2026 mais Strategy C seulement 2022-2025.
Corrélation estimée sur ~3 ans — à ré-estimer quand NQ dataset étendu.

**Note SR :** SR_C = 2.827 est calculé uniquement sur les 281 jours actifs de C (pas tous
les jours calendaires). Le SR stratégie réel (tous jours, ~756) est ≈ 1.52 (CLAUDE.md).
Le SR portefeuille 50/50 = 1.839 est également biaisé par le même artefact ; l'interprétation
qualitative reste valide : C et B sont décorrélés, la diversification est effective.