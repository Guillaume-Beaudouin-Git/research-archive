"""Generate oxfordstrat_109/_INDEX.md — the master registry (curated /resources/ order).
Reuses the verified data captured in oxfordstrat_strategies.xlsx (names, test focus,
rating, URL hyperlinks). Status is tracked here: edit STATUS as strategies are processed.
"""
import os
from openpyxl import load_workbook

XLSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oxfordstrat_strategies.xlsx")
OUT  = os.environ.get("INDEX_OUT",
       "/sessions/serene-elegant-faraday/mnt/data/oxfordstrat_109/_INDEX.md")

# statut par N° (défaut TODO). Met à jour au fil du pipeline.
STATUS = {
    1:  "DISCARD (4/4 FAIL — artefact fill / beta déguisé / DSR / OOS) [REPORT_S001]",
    2:  "DISCARD (1/4 FAIL — Gate 1 artefact fill ; two-sided/DSR/OOS PASS) [REPORT_S002]",
    3:  "DISCARD (2/4 FAIL — beta déguisé + DSR bruit ; Gate1 latence PASS, OOS PASS) [REPORT_S003]",
    4:  "DISCARD (KAMA canonique ER=10 sans edge ; lent = beta long Gate2 + DSR bruit ; Gate1 PASS) [REPORT_S004]",
    5:  "DISCARD (KAMA setup: FastMA=2 whipsaw négatif ; positif que dé-adaptifié = beta long Gate2 + DSR bruit) [REPORT_S005]",
    6:  "DISCARD (3/4 PASS! Donchian breakout vrai signal: Gate1/DSR/OOS OK; meurt Gate2 beta long + MaxDD -70%) [REPORT_S006]",
    7:  "DISCARD (2/4 — Donchian-50+ADX, soeur de #6: vrai signal Gate1+OOS OK mais beta long Gate2 + DSR bruit; ADX inutile; DD -55%) [REPORT_S011]",
    8:  "DISCARD (Aroon Setup: défaut AI=25 sans edge; lent = beta long Gate2 + DSR bruit + décay OOS; Gate1 OK) [REPORT_S007]",
    9:  "DISCARD (3/4 FAIL — Aroon new-high: micro-edge tué par Gate1 latence + beta long Gate2 + DSR bruit; OOS OK) [REPORT_S008]",
    10: "DISCARD (2/4 — Aroon lent AI=100: vrai signal Gate1+OOS OK mais beta long Gate2 + DSR bruit; DD -49%) [REPORT_S009]",
    11: "DISCARD héritage (4/4 — Aroon crossover whipsaw sans edge + beta long Gate2 + DSR bruit + décay OOS) [REPORT_S010]",
    12: "DISCARD (CORRECTION re-audit: l'upgrade BORDERLINE etait une ERREUR. Test propre vs buy&hold APPARIE expo/vol: S012 ne bat PAS le beta -> indices-long recent Sh 0.97 ~= BH 0.93; version low-vol 1.33 < BH-low-vol 1.41 (gain low-vol = mecanique, pas alpha); regime-alpha 10j ~=0. L'alpha-vs-neutre +0.018 du deep-dive etait confondu par la cible/duree de detention (dip vise 0.2->0.8 > neutre 0.5->0.8). Reversion court-terme reelle mais AUCUN edge sur le beta [REPORT_S012 + AUDIT_S012 + AUDIT_S012_deepdive + AUDIT_REAUDIT_all]",
    13: "DISCARD (= #12 exactement au point canonique; re-audit confirme: ne bat pas le buy&hold appariE, regime-alpha ~0. Pas d'edge sur le beta) [REPORT_S013 + AUDIT_REAUDIT_all]",
    14: "DISCARD heritage (2/4 — breakout bande Bollinger = trend; beta long Gate2 (long +0.30/short -0.18) + DSR bruit; Gate1+OOS OK) [REPORT_S014]",
    15: "DISCARD heritage (2/4 — DI-cross Wilder = trend; beta long Gate2 (long +0.060/short -0.034) + DSR bruit; ADXR inutile) [REPORT_S015]",
    16: "DISCARD net 4/4 — 2e MR (Doji counter-trend, archetype distinct): NE MARCHE PAS (perdant des l'origine Sharpe natif -0.60, win 17.7%; pattern Doji alpha NEGATIF -0.01; jamais marche; grille 100% neg). Doji != MR moins decaye que Bollinger [REPORT_S016]",
    17: "DISCARD heritage 4/4 (= Doji counter-trend #16; Body=0.05 strict, sweep Trend x Time; grille 0% positive, win 16.8%, delai+1 -0.61->-0.94) [REPORT_S017]",
    18: "DISCARD heritage 4/4 (Doji-TREND, filtre inverse #16: continuation breakout; net perdant -0.011, grille 0% pos; Gate1 artefact Doji-stop -0.39->-1.53 + Gate2 biais long). Constat: Doji echoue dans LES DEUX sens [REPORT_S018]",
    19: "DISCARD heritage 4/4 (= Doji-trend #18, Body=0.05, sweep Trend x Time; net perdant -0.009, delai+1 -0.24->-1.32). CLOT cluster Doji #16-19: 4 variantes, 4 DISCARD (mecanisme Doji+stop defaillant) [REPORT_S019]",
    20: "DISCARD 2/4 (Donchian Channel E&E1 = channel breakout canonique sans filtre; VRAI signal: Gate1 +0.67->+0.64 PASS (stop au sommet du canal != artefact ORB) + OOS PASS; meurt Gate2 beta long (long +0.43/short -0.20) + DSR bruit; MaxDD -60%. Cluster channel-breakout {#6,#7,#20}=3/3 DISCARD Gate2) [REPORT_S020_donchian]",
    21: "DISCARD heritage 2/4 (Donchian E&E2 = meme entree canal, sortie stop ATR sans cible; PIEGE: expR +1.27/PF 3.7 mais win 7.5%/Sharpe 0.48/MaxDD -88% et 100% long; Gate1 PASS (+0.48->+0.51) + OOS PASS; FAIL Gate2 (long +2.75/short -0.45) + DSR. Cluster channel-breakout {#6,#7,#20,#21}=4/4 DISCARD Gate2) [REPORT_S021_donchian_atr]",
    22: "DISCARD heritage 1/4 (Combined Donchian = vrai Turtle 20/10, sortie trailing canal; MEILLEURE construction du cluster: passe 3/4 -- Gate1 +0.97->+0.65, DSR 1.64>1.52, OOS +0.051->+0.037 -- mais meurt Gate2 beta long (long +0.10/short -0.02). Vrai signal de tendance mais long-beta, pas symetrique; MaxDD -70%. Cluster channel-breakout {#6,#7,#20,#21,#22}=5/5 DISCARD Gate2) [REPORT_S022_combined_donchian]",
    23: "DISCARD 2/4 (Dow Theory MTF = NOUVEL archetype pivots DeMark + filtre tendance primaire multi-echelle, PAS canal/MA; Gate1 PASS (+0.61->+0.46 vrai swing breakout) + OOS PASS; FAIL Gate2 beta long (long +0.068/short -0.020) + DSR. MaxDD -38% (meilleure sortie trailing du lot trend). Meta: 6e mecanisme trend independant a mourir Gate2 - tout 'acheter la force' = beta long) [REPORT_S023_dow_mtf]",
    24: "DISCARD heritage 2/4 (Dow Theory Trend = cas de base mono-echelle de #23, sans filtre primaire, sortie temps; Gate1 PASS marginal (+0.41->+0.09) + OOS PASS; FAIL Gate2 beta long (long +0.087/short -0.056) + DSR. Signal plus faible que #23. Cluster pivot/Dow {#23,#24}=2/2 DISCARD Gate2) [REPORT_S024_dow_trend]",
    25: "DISCARD 2/4 (Dual Momentum ROC = NOUVEL archetype momentum absolu double-confirmation/CTA, lent=filtre rapide=setup, entree breakout extreme; reproduit profil CTA fiche Sharpe 0.59/MaxDD -53%; Gate1 PASS (+0.59->+0.52) + OOS PASS; FAIL Gate2 beta long (long +0.21/short -0.11) + DSR. 8e mecanisme trend a mourir Gate2) [REPORT_S025_dual_momentum_roc]",
    26: "DISCARD heritage 2/4 (Dual Momentum Vortex = meme structure que #25, indicateur Vortex vs ROC; quasi identique comme annonce par la fiche; Gate1 PASS (+0.58->+0.48) + OOS PASS; FAIL Gate2 beta long (long +0.21/short -0.12) + DSR. Cluster dual-momentum {#25,#26}=2/2 DISCARD; 9e mecanisme trend a mourir Gate2) [REPORT_S026_dual_momentum_vortex]",
    27: "DISCARD net 4/4 (Bearish Engulfing = ORB-stop Crabel + setup bougie, PAS du MR close; DECOMPOSITION: pur pattern 10j fwd bull-long +0.37% (=beta marche) / bear-short -0.44% (perd) -> AUCUN alpha de reversal; jambe short -0.15 R win 24% perdante d'origine; combine bilateral 4/4 FAIL edge_pos=False. Etablit archetype cluster Engulfing) [REPORT_S027_engulfing]",
    28: "DISCARD net (Bullish Engulfing = ORB-up long; quasi nul expR -0.003, l'entree ORB NUIT (delai+1 -0.02->+0.49); pur pattern +0.37%=beta; edge_pos=False -> DISCARD 3/4) [REPORT_S028_engulfing_bull]",
    29: "DISCARD heritage 2/4 (Bullish Engulfing Type A = pattern + strict (englobe la range); expR +0.051 mais Gate2 beta long (que des longs) + DSR (Sharpe 0.16); Gate1+OOS PASS) [REPORT_S029_engulfing_bull_a]",
    31: "DISCARD net 4/4 (False Breakout = 1er fade contrarian vrai (Specialists Trap/Turtle Soup); net perdant expR -0.026 Sh -1.32 grille 0% pos; short-fade casse (-0.049), entree-stop artefact de fill (delai+1 -1.32->-0.57); ne bat pas le beta (rec -1.52 vs BH +1.01). Lueur: long-fade +0.023 recent mais mince/unidirectionnel) [REPORT_S031_false_breakout]",
    33: "DISCARD 2/4 (FRAMA Ehlers = breakout bande MA adaptative fractale, entree@open; encore une MA-trend=beta long (long +0.198/short -0.159), DSR bruit; Gate1 faible+OOS PASS; rec +0.27 < BH +1.01) [REPORT_S033_frama]",
    34: "DISCARD 2/4 (Friday Momentum 'One Night Stand' = effet week-end, buy stop vendredi tenu->lundi; CAS D'ECOLE: two-sided+ + OOS+ et beta_bench dit 'BAT le beta' (rec 1.65) MAIS delai+1 INVERSE +1.03->-0.21 = artefact de fill; fiche: mort depuis 1993+couts. Montre qu'il faut combiner beta-test ET delai+1) [REPORT_S034_friday_momentum]",
    35: "DISCARD 1/4 (Gap Pattern Type A, rating B = le + propre near-miss: SEUL edge bilateral non-beta a passer delai+1 (+0.99->+1.11) + two-sided (long +0.043/short +0.018) + OOS; echoue DSR de peu (1.39<1.52) ET surtout DECAYE: Sharpe recent 0.30 << BH recent 1.02 -> ne bat plus le beta. Reel mais en fin de vie) [REPORT_S035_gap_pattern]",
    36: "DISCARD 1/4 (Gap Pattern Type B = #35 avec gap plus lache (Low>Close[i-1]); delai+1 PASS (+1.02->+1.14) + two-sided (long +0.040/short +0.007) + OOS, FAIL DSR (1.02<1.52); decaye rec 0.49 < BH 1.01. Moins efficace que Type A comme l'annonce la fiche. Cluster gap {#35,#36}=2/2 DISCARD) [REPORT_S036_gap_pattern_b]",
    37: "DISCARD 1/4 (Greatest Swing Value = ORB-stop pur, le brouillon parke lors de la correction #20, a son vrai creneau; artefact de fill (delai+1 +1.03->-0.47); passe two-sided+DSR+OOS mais tout l'edge EST le fill; MaxDD -71%. Cluster ORB-stop {#1,#2,#37}=3/3 DISCARD Gate1) [REPORT_S037_gsv]",
    38: "DISCARD 2/4 (GSV-Trend = GSV ORB-stop + filtre tendance (directionnel); beta long (long +0.043/short -0.018) + DSR bruit; delai+1 +0.66->+0.10 (faible) + OOS PASS; rec 0.73 < BH 1.01. Cluster GSV {#37,#38}=2/2 DISCARD) [REPORT_S038_gsv_trend]",
    39: "DISCARD net 3/4 (Heikin-Ashi Setup&Exit = trend-follower bougies lissees, entree@open; ~nul expR -0.001, beta long (long +0.029/short -0.036), DSR fail, OOS flip; edge_pos=False. HA = suivi de tendance = beta sans alpha) [REPORT_S039_heikin_ashi]",
    40: "DISCARD net 4/4 (Heikin-Ashi Setup&Filter = #39 + filtres corps/tendance + sortie flip HA; net perdant expR -0.002 grille 0% pos, 4/4 FAIL. Cluster Heikin-Ashi {#39,#40}=2/2 DISCARD) [REPORT_S040_heikin_ashi_filter]",
    41: "DISCARD 3/4 (Hikkake = inside-bar false breakout, fade-fakeout two-sided; net ~nul expR +0.0025 Sh 0.07; delai+1 PASS mais FAIL Gate2 beta + DSR + OOS flip; rec -0.40 < BH 1.01) [REPORT_S041_hikkake]",
    42: "DISCARD 3/4 (Modified Hikkake = #41 fakeout plus lache (close plus bas); a peine mieux (Sh 0.18) comme l'annonce la fiche; FAIL Gate2 beta + DSR + OOS flip. Cluster Hikkake {#41,#42}=2/2 DISCARD) [REPORT_S042_hikkake_modified]",
    43: "DISCARD 1/4 (Hook Crabel = ORB-stop + setup hook (gap avorte); two-sided+ (long +0.105/short +0.074) + OOS+ MAIS le fill ORB porte l'edge (delai+1 +0.33->+0.03) et ne bat pas le beta (rec 0.57<1.01); DSR fail) [REPORT_S043_hook]",
    44: "DISCARD net 4/4 (Hook Bearish = jambe short #43; artefact de fill (delai+1 +0.18->-0.01) + OOS flip) [REPORT_S044_hook_bear]",
    45: "DISCARD 2/4 (Hook Bullish = jambe long #43, la + propre: delai+1 PASS (+0.29->+0.06) + OOS PASS (+0.09->+0.13) mais unidirectionnel=beta (FAIL two-sided) + DSR; rec 0.53<BH 1.06. Cluster Hook {#43,#44,#45}=3/3 DISCARD) [REPORT_S045_hook_bull]",
    46: "DISCARD 2/4 (Hull MA = dual-HMA slope trend; beta long (long +0.25/short -0.17) + DSR; delai+1+OOS PASS; rec 0.27 < BH 1.01) [REPORT_S046_hull_ma]",
    47: "DISCARD net 4/4 (Keltner 2-Phase = breakout canal always-in; net perdant expR -0.007 Sh -0.23, beta, sur-trade. edge_pos=False) [REPORT_S047_keltner_2phase]",
    48: "DISCARD net 4/4 (Keltner 3-Phase = #47 + phase neutre; toujours net perdant -0.007 Sh -0.35. Cluster Keltner {#47,#48}=2/2 DISCARD net) [REPORT_S048_keltner_3phase]",
    49: "DISCARD 2/4 (LR Slope = double pente regression >0 = beta long (long +0.21/short -0.13) + DSR; delai+1+OOS PASS; rec 0.31 < BH 1.01) [REPORT_S049_lr_slope]",
    50: "DISCARD 2/4 (LR Slope Normalized = LRS/ATR; meilleur Sharpe du lot (0.57) mais toujours beta long (long +0.43/short -0.17) + DSR; rec 0.49 < BH 1.01; MaxDD -64%. Cluster LR {#49,#50}=2/2 DISCARD) [REPORT_S050_lr_slope_norm]",
    51: "DISCARD 2/4 (Long Equity Babcock = momentum long-only sur indices; win 92% (exit 1er open profitable); beta_bench 'bat le beta' rec 1.34 mais SEULEMENT au fill optimiste (delai+1 +0.72->+0.13); long-only=beta, two-sided N/A + DSR) [REPORT_S051_long_equity]",
    52: "DISCARD 2/4 (MACD Part 1 = zero-cross EMA; beta long (long +0.39/short -0.16) + DSR; delai+1+OOS PASS; rec 0.63 < BH 1.01) [REPORT_S052_macd]",
    53: "DISCARD 2/4 (MACD Part 2 = #52 + ligne signal; Sharpe 0.37 < 0.53 (pire, comme la fiche); beta long + DSR. Cluster MACD {#52,#53}=2/2 DISCARD) [REPORT_S053_macd2]",
    54: "DISCARD net 4/4 (Multiple Time Frames Babcock = alignement tendance 3 echelles; net perdant expR -0.002 Sh -0.11, sur-trade; edge_pos=False) [REPORT_S054_mtf]",
    55: "DISCARD net 4/4 (Narrow Range N-Day = NR Crabel + ORB-stop; artefact de fill (delai+1 +0.21->-0.88) + OOS flip. Cluster ORB-stop {#1,#2,#37,#55}=4/4 DISCARD Gate1) [REPORT_S055_narrow_range]",
    56: "DISCARD 3/4 (NR7 Crabel + ORB-stop; artefact de fill (delai+1 +0.26->-0.98) + DSR + OOS flip. Fiche: 'non tradeable apres couts'. Cluster ORB-stop/NR 5/5 DISCARD) [REPORT_S056_nr7]",
    57: "DISCARD doublon (= #34 'One Night Stand'/Friday Momentum, MEME URL; artefact de fill, voir REPORT_S034) [REPORT_S057_one_night_stand]",
    58: "DISCARD 2/4 (Oops gap-fade two-sided; delai+1 PASS (+0.79->+0.58) + OOS, FAIL Gate2 (long +0.061/short -0.006 asymetrique) + DSR; rec 0.74<BH 1.01. Le long porte tout -> voir #60) [REPORT_S058_oops]",
    59: "DISCARD net 4/4 (Oops Bearish = gap-up-fade short; perdant -0.016 Sh -0.47, artefact + OOS flip. Fade la force = perd) [REPORT_S059_oops_bear]",
    60: "BORDERLINE (RETROGRADE de KEEP apres audit 2026-06-07 — Sharpe gonfle par artefact de methode). Oops Bullish gap-down-fade long-only. CORRECTION: le deep-dive annoncait Sh 2.9-3.1/beta~0 mais le PnL quotidien etait construit par R ETALE sur la detention -> vol ecrasee (1.1% vs 3.4% reels) -> Sharpe x3 et beta biaise vers 0. Recalcul MARK-TO-MARKET: Sharpe 0.70 brut / 0.41 couvert-beta (deployable delai+1); alpha NON significatif sur indices=donnees propres (t=0.61). Ce qui tient: edge PAR TRADE positif (indices expR +0.031 IC95 [+0.014,+0.050]>0). Edge reel mais MODESTE. VALIDE SUR DONNEES FTMO REELLES (Algo_claude/data: indices vrai OHLC + or M1 2007+ + crypto): edge par trade confirme (deployable expR +0.034 IC95 [+0.016,+0.051]>0) MAIS alpha couvert-beta NON significatif (t_NW=0.61 indices/0.79 deploy, Sharpe couvert ~0.12-0.15). Le marginal venait de commodites proxy (softs/argent/PT/PD/oil = pas d'OHLC FTMO reel). Effet reel mais trop faible pour exploitation seule -> NE SATISFAIT PAS KEEP. Compteur KEEP=0. Voir AUDIT_DOSSIER_S060.md s11-12) [REPORT_S060_oops_bull]",
    61: "DISCARD 1/4 (ORB canonique Crabel = pilier de la famille; edge = pur artefact de fill intrabar: natif Sh +1.17 -> delai+1 -0.65 (inversion). Ne bat pas le beta (rec 1.08 vs BH 1.01). Gabarit ORB-stop) [REPORT_S061_orb]",
    62: "DISCARD 2/4 (ORB barres hebdo; survit delai+1 faible (+0.52->+0.11) mais two-sided=beta long (long +0.38/short -0.16) + DSR bruit; rec 0.79<BH 1.01. La fiche: 'mort une fois les couts appliques') [REPORT_S062_orb_weekly]",
    63: "DISCARD 2/4 (ORBP Counter-Trend = ORB cote contre-tendance; artefact de fill (delai+1 +0.43->-0.12) + beta long deguise (long +0.047/short -0.020); rec -0.10<BH 1.01. Le filtre fade n'ajoute rien) [REPORT_S063_orbp_ct]",
    64: "DISCARD 1/4 (ORBP Momentum Filter, rating C; SEUL ORB a REPARER l'artefact de fill: delai+1 +0.80->+0.30 PASS + DSR 2.07 + OOS stables. MAIS two-sided=beta long (long +0.043/short -0.016) et NE BAT PAS le beta (rec 0.82<BH 1.01): le filtre transforme l'ORB en proxy de tendance long. Demasque par le 5e test, pas les 4 gates) [REPORT_S064_orbp_trend]",
    65: "DISCARD 3/4 (ORBP Price Channel Filter Donchian, rating C; artefact de fill revient (delai+1 +0.42->-0.04, la cassure de canal = jour de fill le + optimiste) + beta long + DSR bruit; rec 0.61<BH 1.01. Pire que #64) [REPORT_S065_orbp_channel]",
    66: "DISCARD 4/4 + NON reproductible FTMO (Pathfinder intermarche devises, Freeburg; archetype intermarche NEUF mais le filtre DEFINISSANT = T-bonds, ABSENT de l'univers FTMO. De plus la source (Table 2) montre que le filtre a DECAYE: ameliore la base 1980-95 (Sh 0.88 vs 0.79) mais la DEGRADE 1996-2015 (Sh 0.06 vs 0.17). Cas de base FTMO (dual-MA devises) sans edge: 4/4, edge_pos=False) [REPORT_S066_pathfinder]",
    67: "DISCARD 1/4 (Price Breakout NR7 Setup&Exit, Crabel+Connors/Raschke; NR7 + cassure canal Donchian-1. Artefact de fill SPECTACULAIRE: natif +0.21 -> delai+1 -1.39 (inversion la + violente du projet). Fiche: 'non tradeable apres couts, ~ NR7-ORB'. Changer l'entree (canal vs ORB) ne change rien=meme stop intrabar) [REPORT_S067_pricebreak_nr7]",
    68: "DISCARD 4/4 (Price Breakout NR7 Setup&Entry, jumeau de #67 balayant Channel_Length; elargir le canal DETRUIT l'edge: seul CL1(=#67) positif, CL>=5 negatif. La zone 'CL>=10' vantee par la fiche est NEGATIVE apres couts FTMO. delai+1 -0.43, edge_pos=False. Cluster PB-NR7 2/2 DISCARD) [REPORT_S068_pricebreak_nr7_entry]",
    69: "DISCARD 2/4 (Price Momentum benchmark Kaufman; dual-momentum trend M1&M2>0. Survit delai+1 (+0.36, entree@open) + OOS, MAIS two-sided=beta long (long +0.070/short -0.044) + DSR bruit; rec 0.30<BH 1.01. Proxy de tendance long=beta. Cluster trend/momentum maintenu) [REPORT_S069_price_momentum]",
    70: "DISCARD 4/4 (Profit-Taking Kaufman P1, etude de sortie; systeme EMA-turn NET PERDANT Sh -0.71 (4/4 edge_pos=False). ET reproduit le resultat de la fiche qui CONTREDIT Kaufman1995: les cibles de profit DEGRADENT (expR sans cible -0.092 > cible20% -0.115). Lecon: regle de sortie sur petit echantillon ne survit pas OOS) [REPORT_S070_profit_taking]",
    71: "DISCARD (= #70, jumeau; meme strategie EMA-turn + cible%, periode 2000-2011. Systeme net perdant 4/4 + cibles degradent. Voir REPORT_S070) [REPORT_S071_profit_taking_p2]",
    72: "DISCARD (RSI2 Connors dip-buy: VRAIE mean-reversion mais DECAYEE/arbitree. Survit delai+1 (1.33->1.31) ; MTM alpha couvert-beta significatif PLEIN echantillon (Sh couvert 0.52 t_NW 2.62) MAIS par periode: 2000-09 Sh couvert 0.92 (t2.9) -> 2010-18 0.47 (t1.4) -> 2019-26 -0.04 (t-0.09 MORT). Connors a publie RSI2 en 2009 -> edge arbitre apres pub. Gates 2/4 (two-sided long-only + DSR limite). Non deployable: edge recent nul) [REPORT_S072_rsi2]",
    73: "DISCARD (= #72; RSI2 meme entree, sortie RSI au lieu de MA. Fiche: 'ni mieux ni pire que #72'. MTM identique (Sh couvert 0.52 t2.65) -> meme decroissance, mort 2019-26. Gates 1/4 (two-sided long-only). Cluster RSI2 2/2 DISCARD) [REPORT_S073_rsi2_exits]",
    74: "DISCARD 2/4 (Reversal Patterns P1, pivots offre/demande Wyckoff/Crabel, archetype neuf 2-cotes; win 29% gros RR. Survit delai+1 mais two-sided=beta long (long +0.042/short -0.011) + DSR bruit; rec 0.52<BH 1.01. Seuls gros RR positifs=tres sensible aux couts comme dit la fiche) [REPORT_S074_reversal]",
    75: "DISCARD 2/4 (Reversal Patterns P2 = #74 + filtre divergence MACD; reduit trades/DD mais meme verdict: beta long (long +0.039/short -0.006) + DSR bruit; rec 0.78<BH 1.01. Divergence 'ajoute de la valeur' a la marge mais insuffisant. Cluster Reversal 2/2 DISCARD) [REPORT_S075_reversal2]",
    76: "KEEP (PREMIER KEEP DU PROJET, promu apres deep-dive complet AUDIT_DOSSIER_S076) Ross Hook (Joe Ross), continuation de breakout court terme. 4 GATES 0/4. DEEP-DIVE: anti-look-ahead OK (robuste delai+2/+3/+5), alpha SIGNIFICATIF sur DONNEES FTMO REELLES t_NW=4.0 (le test que #60 echouait), distinct beta marche (b~0) ET beta tendance (corr TSMOM 0.11, alpha t=5.4 vs marche+TSMOM), STABLE 2000-09/2010-18/2019-26, MaxDD reel -6%, skew +2.32, robuste couts (+10bps). Cadrage honnete: ~60% prime breakout-momentum generique + ~40% selectivite hook. Reserves: forex faible (retirer), part commodites=proxy (revalider), effet lent. Config: indices+commodites+crypto) [REPORT_S076_ross_hook]",
    77: "KEEP (= #76, Ross Hook + filtre profondeur Setup&Filter; gates 0/4, edge identique). Voir AUDIT_DOSSIER_S076) [REPORT_S077_ross_hook_setupfilter]",
    78: "KEEP (= #76, rating B source; Ross Hook + filtre profondeur + time exit; gates 0/4, grille positive partout). Voir AUDIT_DOSSIER_S076) [REPORT_S078_ross_hook_filter]",
    79: "KEEP (= #76, rating B; Ross Hook Exit2 holding plus long; Sharpe 1.87, gates 0/4. Cluster Ross Hook {76-79}=4/4 KEEP). Voir AUDIT_DOSSIER_S076) [REPORT_S079_ross_hook_exit2]",
    80: "DISCARD 2/4 (SMA dual trend Kaufman = beta long classique: long +0.89/short -0.18 le short perd, rec 0.79<BH 1.01. CONTROLE PROPRE: echoue la ou Ross Hook passe sur le meme univers -> l'edge #76 n'est pas 'la tendance marche' mais la selectivite du hook) [REPORT_S080_sma]",
    81: "DISCARD 3/4 (Smash Day Type A Williams, reversal jour-avorte: up-day cloture faible -> buy stop au-dessus du high. Net perdant expR -0.009 edge_pos=False; fill optimiste PIRE que reel (-0.18->+0.35=achat du plus-haut d'un jour reversal); two-sided long-biais + DSR bruit + OOS flip; rec -0.15<BH 1.01) [REPORT_S081_smashday_a]",
    82: "DISCARD 3/4 (= #81 Type A, etude sortie Time=20; net perdant -0.008, edge_pos=False. Allonger la detention ne sauve rien) [REPORT_S082_smashday_a_exits]",
    83: "DISCARD 3/4 (Smash Day Type B Williams, RATING B source NON confirme: close<low veille=smash -> buy stop au-dessus du high. Natif Sh 0.00 -> delai+1 +1.15 (artefact INVERSE de fill, fragile); two-sided=beta long (long+0.011/short-0.013) + DSR bruit (0.13) + OOS flip; rec 0.01<BH 1.01. Le B sur 42 futures 1980-2011 ne traduit pas sur FTMO) [REPORT_S083_smashday_b]",
    84: "DISCARD 3/4 (= #83 Type B rating B, etude sortie Time=20; net plat/negatif -0.001 edge_pos=False; meme artefact inverse de fill. Cluster Type B 2/2 DISCARD) [REPORT_S084_smashday_b_exits]",
    85: "DISCARD 3/4 (Smash Day Type C = Type B SANS filtre, rating D; net perdant -0.36 rec -1.02<BH 1.01; retirer le filtre degrade encore. Cluster Smash Day {81-85}=5/5 DISCARD: l'entree stop au-dela de l'extreme d'un jour de smash achete de mauvais prix et ne bat jamais le beta) [REPORT_S085_smashday_c]",
    86: "DISCARD 4/4 (TD Sequential DeMark, exhaustion MR; net perdant -0.008 edge_pos=False. Instructif: jambe LONG (achat epuisement baissier apres 9-setup+13-countdown) expR +0.095 POSITIF, mais SHORT perd -0.072 (vendre la force = perd) -> net negatif apres couts; rec 0.43<BH 1.01. Simplif: intersection assumee, methode-2) [REPORT_S086_td_sequential]",
    87: "DISCARD 2/4 (Livermore System P1, pivots swing = 'average momentum model' dixit source; proxy Donchian-regime. two-sided=beta long (long +0.245/short -0.215 le short perd) + DSR bruit; rec 0.13<BH 1.01. Cf #69/#80) [REPORT_S087_livermore]",
    88: "DISCARD 2/4 (= #87 Livermore P2, 2e etude filtres; meme momentum-beta long +0.378/short -0.250, rec 0.35<BH 1.01. Cluster Livermore 2/2 DISCARD) [REPORT_S088_livermore2]",
    89: "DISCARD 3/4 (Turtle Soup Connors/Raschke, fade false-breakout 20j; net perdant -0.003 edge_pos=False; artefact inverse de fill (natif -0.07->delai+1 +0.81); win 12%; rec 0.09<BH 1.01. Coherent avec False Breakout #31/#32 et rating D) [REPORT_S089_turtle_soup]",
    90: "DISCARD 3/4 (= #89 Turtle Soup Exit2 canal rapide; net perdant -0.006 edge_pos=False. Cluster Turtle Soup 2/2; avec False Breakout {31,32} le fade de cassure 20j = 4/4 DISCARD sur FTMO) [REPORT_S090_turtle_soup2]",
    91: "DISCARD 2/4 (Volatility Squeeze Bollinger; la source dit que le filtre squeeze N'AMELIORE PAS la base trend Bollinger. Base testee = beta long (long +0.217/short -0.146), rec 0.14<BH 1.01. Cf #14) [REPORT_S091_vol_squeeze]",
    92: "DISCARD 2/4 + filtre volume NON reproductible FTMO (Volume Filters P1 Edwards/Magee+Donchian; CFD sans volume centralise. La source montre que le volume DEGRADE: Sh 0.95 off->0.81 on. Base price-breakout testee = beta long +0.656/short -0.256, rec 0.38<BH 1.01. Cf #20-22) [REPORT_S092_volume_filters]",
    93: "DISCARD (= #92, Volume Filters P2; volume non reproductible + base breakout beta. La serie conclut que le volume n'aide pas) [REPORT_S093_volume_filters2]",
    94: "DISCARD (= #92, Volume Filters P3; volume non reproductible + base breakout beta. Cluster Volume Filters {92,93,94}=3/3 DISCARD) [REPORT_S094_volume_filters3]",
    95: "DISCARD 2/4 (Vortex Indicator VI+/VI- crossover = momentum/trend long deguise: long +0.038/short -0.032 le short perd, rec 0.67<BH 1.01. Cf cluster trend #69/#80/#87) [REPORT_S095_vortex]",
    96: "DISCARD 2/4 (Wide Range N-Day Crabel = ORB-stop sur jours wide-range; artefact de fill (natif +1.04->delai+1 -0.11) + DSR bruit. Source: NET PERDANT Sh -1.45 MaxDD -88%, pire que Narrow Range. Famille ORB-stop #55/#56/#37/#61) [REPORT_S096_wide_range]",
    97: "DISCARD 2/4 (Wilder Volatility Breakout, stop-and-reverse SAR/ATR = trend long deguise: long +0.099/short -0.071 le short perd, rec 0.37<BH 1.01. Cluster trend) [REPORT_S097_wilder_vol]",
    98: "DISCARD 4/4 (Wyckoff Mean Reversion, fade bull/bear-trap; NET PERDANT expR -0.013 Sh -0.89 edge_pos=False, rec -1.05<BH 1.01, grille negative partout. Famille fade=False Breakout/Turtle Soup/Reversal, toutes DISCARD) [REPORT_S098_wyckoff]",
    99: "DISCARD 3/4 (= #98 Wyckoff Risk-Reward; net -0.005 edge_pos=False. Varier RR ne sauve pas une entree a esperance negative) [REPORT_S099_wyckoff_rr]",
    100: "DISCARD 3/4 (= #98 Wyckoff Time Exits; ~zero expR +0.002, rec 0.17<BH. Cluster Wyckoff 3/3; toute la famille fade false-breakout = 0 edge sur FTMO) [REPORT_S100_wyckoff_time]",
    101: "DISCARD 2/4 (Zero Lag MA Ehlers, crossover ZLMA/EMA = trend long deguise: long +1.38/short -0.15, rec 0.94<BH 1.01, DSR bruit. Source: 'pas mieux que Hull MA'. Cluster trend) [REPORT_S101_zlma]",
    102: "DISCARD (= #101, ZLMA Entry&Filter; meme crossover + filtre seuil; trend long beta) [REPORT_S102_zlma_filter]",
    103: "DISCARD (= #86, TD Sequential Adjusted countdown&exit, Ind; heritage du TD Seq DISCARD 4/4 net perdant) [REPORT_S103_td_seq_adjusted]",
    104: "DISCARD 3/4 (TD Setup-Trend DeMark, Ind; 9-setup en momentum continuation: ~zero expR +0.0015, long beta, OOS flip, rec -0.09<BH) [REPORT_S104_td_setup_trend]",
    105: "DISCARD (= #86, TD Sequential countdown&exit, Ind; cluster TD Seq {86,103,105}=3/3 DISCARD) [REPORT_S105_td_seq_countdown]",
    106: "HORS-SCOPE (Data: Global Market Correlations 1995-2014; etude de donnees, pas une strategie -> aucun backtest) [REPORT_S106_data]",
    107: "HORS-SCOPE (Data: Volatility Clustering P1; etude de donnees, non-tradable) [REPORT_S107_data]",
    108: "HORS-SCOPE (Data: Volatility Clustering P2; etude de donnees, non-tradable) [REPORT_S108_data]",
    109: "HORS-SCOPE (Data: Volatility Clustering P3; etude de donnees, non-tradable) [REPORT_S109_data]",
    32: "DISCARD net (= #31 fade, sortie trailing channel; net perdant expR -0.005 grille 0% pos; long-fade le + positif du cluster (+0.065, fill reel Sh +0.60) mais short casse (-0.045) et NE BAT PAS le beta (rec +0.09 vs BH +1.01). Cluster False Breakout {#31,#32}=2/2 DISCARD) [REPORT_S032_false_breakout_trail]",
    30: "DISCARD heritage 2/4 (Bullish Engulfing Type A + dip-filter Close<MA; expR BRUT le + eleve du cluster +0.51/PF1.71 MAIS mirage: 255 trades, Sharpe 0.25, DSR fail, strictement long=beta repli; expR eleve != KEEP. Cluster Engulfing 4/4 DISCARD; bilan bougies Doji+Engulfing=8/8 DISCARD) [REPORT_S030_engulfing_bull_a_filter]",
}

wb = load_workbook(XLSX); ws = wb["All Strategies"]
rows = []
r = 5
while ws.cell(r, 3).value:
    n      = ws.cell(r, 1).value
    sect   = ws.cell(r, 2).value
    name   = ws.cell(r, 3).value
    test   = ws.cell(r, 4).value or ""
    rating = ws.cell(r, 5).value
    lc     = ws.cell(r, 6)
    url    = lc.hyperlink.target if lc.hyperlink else ""
    rows.append((n, sect, name, test, rating, url))
    r += 1

def status(n):
    return STATUS.get(n, "TODO")

lines = []
lines.append("# Registre maître — oxfordstrat 109 (pipeline v2-gates)\n")
lines.append("Ordre **figé** = liste curatée de https://oxfordstrat.com/resources/ "
             "(linéaire, ~alphabétique). *Ce n'est PAS* l'ordre de l'archive "
             "`/trading-strategies/` (anti-chronologique, paginée).\n")
lines.append(f"- Total entrées : **{len(rows)}** "
             f"({sum(s=='Strategy' for _,s,_,_,_,_ in rows)} stratégies + "
             f"{sum(s=='Indicator' for _,s,_,_,_,_ in rows)} indicateurs + "
             f"{sum(s=='Data Analysis' for _,s,_,_,_,_ in rows)} analyses de données)")
done = sum(1 for n,*_ in rows if status(n) != "TODO")
verdicts = " · ".join(f"S{n:03d}={STATUS[n].split(' ')[0]}" for n in sorted(STATUS))
lines.append(f"- Traitées : **{done}/{len(rows)}** · Verdicts : {verdicts}")
lines.append("- Rating site = note publiée par oxfordstrat (A meilleur → D). "
             "Statut = verdict de NOTRE pipeline v2-gates.")
lines.append("- ⚠️ **Décalage de nommage** (la #7 avait été sautée puis rattrapée) : les fichiers "
             "`REPORT_S007–S010` correspondent aux **#8–#11** ; la **#7** est dans `REPORT_S011`. "
             "Le statut de chaque ligne indique son fichier-rapport entre crochets.\n")
lines.append("| N° | Sec | Stratégie | Test | Rating site | Statut pipeline | Fiche |")
lines.append("|---:|---|---|---|:---:|---|---|")
sec_abbr = {"Strategy": "S", "Indicator": "Ind", "Data Analysis": "Data"}
for n, sect, name, test, rating, url in rows:
    st = status(n)
    nm = f"**{name}**" if n == 1 else name
    lines.append(f"| {n} | {sec_abbr.get(sect,sect)} | {nm} | {test} | {rating} | {st} | [lien]({url}) |")
lines.append("\n*Maj statut : éditer `STATUS` dans `code/build_index.py` puis relancer.*")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(lines))
print("wrote", OUT, "|", len(rows), "rows | done:", done)
for n, sect, name, test, rating, url in rows[1:5]:
    print(f"  #{n}: {name} ({test}) [{rating}] {url}")
