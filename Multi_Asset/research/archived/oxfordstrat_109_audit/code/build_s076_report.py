"""Build the institutional due-diligence PDF for #76 Ross Hook (reportlab)."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
OUT = os.path.join(HERE, "..", "RAPPORT_INSTITUTIONNEL_S076_RossHook.pdf")
NAVY = colors.HexColor('#1f3864'); STEEL = colors.HexColor('#2e5b9a'); LGREY = colors.HexColor('#eef1f6')
GREEN = colors.HexColor('#1e7d4f'); RED = colors.HexColor('#b3261e')

ss = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=ss['Heading1'], textColor=NAVY, fontSize=15, spaceBefore=10, spaceAfter=6)
H2 = ParagraphStyle('H2', parent=ss['Heading2'], textColor=STEEL, fontSize=11.5, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle('BODY', parent=ss['Normal'], fontSize=9.2, leading=13, alignment=TA_LEFT, spaceAfter=5)
SMALL = ParagraphStyle('SMALL', parent=ss['Normal'], fontSize=7.6, leading=10, textColor=colors.HexColor('#555555'))
CELL = ParagraphStyle('CELL', parent=ss['Normal'], fontSize=8.2, leading=10)
CELLB = ParagraphStyle('CELLB', parent=CELL, fontName='Helvetica-Bold')
TITLE = ParagraphStyle('TITLE', parent=ss['Title'], textColor=NAVY, fontSize=23, leading=27)
SUB = ParagraphStyle('SUB', parent=ss['Normal'], fontSize=12, textColor=STEEL, alignment=TA_CENTER, spaceAfter=2)
CENTER = ParagraphStyle('CENTER', parent=ss['Normal'], fontSize=9.5, alignment=TA_CENTER, textColor=colors.HexColor('#444'))

story = []
def hr(): story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor('#c9d2e0'), spaceBefore=4, spaceAfter=8))

def kv_table(rows, col_w, header=True):
    t = Table(rows, colWidths=col_w)
    st = [('FONT',(0,0),(-1,-1),'Helvetica',8.4),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
          ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#cfd6e4')),
          ('ROWBACKGROUNDS',(0,1 if header else 0),(-1,-1),[colors.white, LGREY]),
          ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
          ('LEFTPADDING',(0,0),(-1,-1),5)]
    if header:
        st += [('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONT',(0,0),(-1,0),'Helvetica-Bold',8.6)]
    t.setStyle(TableStyle(st)); return t

# ---------------- COVER ----------------
story += [Spacer(1, 3.2*cm),
          Paragraph("Ross Hook", TITLE),
          Paragraph("Stratégie systématique de continuation de breakout", SUB),
          Paragraph("Rapport de due-diligence — usage interne / comité d'investissement", SUB),
          Spacer(1, 0.8*cm), HRFlowable(width="60%", thickness=1.2, color=NAVY), Spacer(1, 0.5*cm),
          Paragraph("Univers : 30 CFD FTMO (indices, commodités, FX, crypto) &nbsp;·&nbsp; Période : 2000–2026 &nbsp;·&nbsp; Données journalières", CENTER),
          Paragraph("Statut : <b>KEEP</b> (1er sur 80 stratégies évaluées) &nbsp;·&nbsp; Réf. registre #76 &nbsp;·&nbsp; Moteur ftmo_lab @ 9dea332", CENTER),
          Spacer(1, 0.3*cm), Paragraph("Date : 7 juin 2026", CENTER),
          Spacer(1, 2.2*cm)]
disc = ("<b>Avertissement.</b> Performances simulées (hypothétiques), hors-échantillon partiel, sur données dont une partie "
        "(commodités hors or) provient de futures continus proxy. Résultats backtest ≠ performance future. Document de "
        "recherche interne destiné à un audit indépendant ; ne constitue ni un conseil en investissement ni une sollicitation.")
story += [kv_table([[Paragraph(disc, SMALL)]], [16.4*cm], header=False), PageBreak()]

# ---------------- 1. EXECUTIVE SUMMARY ----------------
story += [Paragraph("1. Résumé exécutif", H1), hr()]
thesis = ("Le <b>Ross Hook</b> est une stratégie systématique de <b>continuation de breakout à court terme</b>, "
          "bidirectionnelle, tenue ~11 jours, déployée sur un univers diversifié de CFD FTMO. Elle achète (resp. vend) "
          "la <b>reprise d'un nouveau plus-haut (resp. plus-bas) sur 10 jours après sa première correction</b>. "
          "C'est la <b>seule stratégie sur 80 évaluées</b> à franchir l'intégralité du protocole de validation : 4 gates, "
          "audit mark-to-market, neutralité au facteur tendance, test de causalité, et validation sur données FTMO réelles.")
story += [Paragraph(thesis, BODY)]
story += [Paragraph("Indicateurs clés (portefeuille déployable hors-FX, mark-to-market, exécution à J+1)", H2)]
exec_rows = [
 ["Performance","Valeur","Risque","Valeur","Validation","Statut"],
 ["CAGR","+4,1 %","Max Drawdown","−5,2 %","4 Gates constitutionnels","4/4 ✓"],
 ["Volatilité ann.","4,2 %","Durée max DD","~430 j","Causalité (anti-look-ahead)","PASS ✓"],
 ["Sharpe","0,98","VaR 95 % (jour)","−0,36 %","Alpha vs marché+tendance","t = 5,6 ✓"],
 ["Sortino","1,42","CVaR 95 %","−0,55 %","Données FTMO réelles","t = 4,0 ✓"],
 ["Calmar","0,79","Skew (quotidien)","+2,32","Robuste coûts (+10 bps)","Sh 1,1 ✓"],
 ["Alpha annualisé","+4,5 %","Skew (par trade)","+4,81","Vivant en récent (2019-26)","Sh 1,05 ✓"],
]
story += [kv_table(exec_rows, [3.0*cm,2.1*cm,3.0*cm,2.1*cm,4.2*cm,2.0*cm])]
story += [Spacer(1,6)]
verdict = ("<b>Conclusion.</b> Edge réel, statistiquement significatif (alpha t=5,6 après contrôle marché + tendance), "
           "<b>distinct du beta actions (β≈0) et du beta tendance/CTA (corr 0,11)</b>, persistant sur trois sous-périodes "
           "disjointes (y compris 2019-2026), à <b>convexité positive</b> (+24 % en 2008, +20 % en 2020) et drawdown "
           "maîtrisé (−5,2 %). <b>Recommandation : retenir pour paper-trading / allocation pilote</b>, après les réserves §8.")
story += [kv_table([[Paragraph(verdict, CELL)]], [16.4*cm], header=False)]
story += [Spacer(1,6),
          Paragraph("Cadrage honnête : ~60 % de la performance provient d'une prime générique de breakout-momentum court "
                    "terme (acheter les nouveaux plus-hauts est déjà rentable), ~40 % de la sélectivité du « hook ». "
                    "Ce n'est pas un alpha propriétaire unique mais une <b>implémentation robuste d'une prime connue</b>, "
                    "correctement isolée du beta.", SMALL)]
story += [PageBreak()]

# ---------------- 2. STRATEGY ----------------
story += [Paragraph("2. Description de la stratégie", H1), hr(),
          Paragraph("2.1 Concept (Joe Ross)", H2),
          Paragraph("Le Ross Hook est une entrée de continuation : après la cassure confirmée d'une tendance "
                    "(pattern 1-2-3), la <b>première correction</b> (le « hook ») est statistiquement suivie d'une reprise. "
                    "On se positionne sur la reprise, dans le sens de la tendance.", BODY),
          Paragraph("2.2 Règles exactes implémentées (proxy)", H2)]
rules = [
 ["Élément","Règle (côté long ; short = miroir)"],
 ["Jambe / breakout","high[i] = plus-haut sur Min_Setup=10 barres ET high[i] > high[i−1]  →  niveau H*"],
 ["Correction (hook)","≥ 1 barre ultérieure avec high < H* ; plus-bas atteint = hook low"],
 ["Entrée","reprise high ≥ H* dans Max_Hook=20 barres → achat ; exécution à l'OPEN du lendemain (J+1)"],
 ["Sorties","quick-stop (hook low) | stop ATR 6×ATR(20) | sortie temporelle 10 jours"],
 ["Sizing","fixed-fractional 0,5 % du capital par trade ; R normalisé par 6×ATR"],
 ["Coûts","spread + commission + slippage, planchonnés par classe (1,5–8,0 bps round-turn)"],
]
story += [kv_table(rules, [3.6*cm, 12.8*cm])]
story += [Spacer(1,6),
          kv_table([[Paragraph("<b>⚠ Divergence à auditer.</b> Le moteur teste un <b>proxy</b> : « nouveau plus-haut 10 barres » "
                    "remplace la détection formelle du pattern 1-2-3. Plus permissif que Joe Ross littéral. "
                    "Question ouverte pour l'équipe : l'implémentation du 1-2-3 strict modifie-t-elle l'edge ? "
                    "(Hypothèse : marginalement — l'effet est lent et largement du breakout-momentum.)", CELL)]],
                   [16.4*cm], header=False)]

# ---------------- 3. UNIVERSE & DATA ----------------
story += [Paragraph("3. Univers & données", H1), hr()]
data_rows = [
 ["Classe","Instr.","Source","Période","Qualité / réserve"],
 ["Indices","10","Panel type-FTMO","2000–2026","Référence (vrai OHLC)"],
 ["Commodités","9","Futures continus Yahoo (or : M1)","2005–2026","Proxy — à revalider sur données broker"],
 ["Crypto","2","M1 rééchantillonné","2017/18–2026","Échantillon court"],
 ["FX","9","M1 rééchantillonné","2018–2026","Edge non significatif → EXCLU du déployable"],
]
story += [kv_table(data_rows, [2.6*cm,1.3*cm,5.4*cm,2.6*cm,4.5*cm]),
          Spacer(1,5),
          Paragraph("Le portefeuille <b>déployable</b> retenu = indices + commodités + crypto (FX exclu). Breadth croissante : "
                    "~16 instruments en 2005 → ~21 dès 2018. Le moteur de backtest partagé (ftmo_lab.py) est figé et inchangé "
                    "(commit 9dea332) sur l'ensemble des 80 stratégies — il n'a pas été ajusté pour cette stratégie.", BODY)]

# ---------------- 4. METHODOLOGY ----------------
story += [Paragraph("4. Méthodologie de validation", H1), hr(),
          Paragraph("Chaque stratégie passe un protocole pré-enregistré et identique. Une stratégie n'est retenue (KEEP) "
                    "que si elle franchit les cinq niveaux :", BODY)]
meth = [
 ["Niveau","Test","Critère"],
 ["1","Gate délai+1 (réalisme d'exécution)","l'edge survit à l'exécution à l'open suivant (pas un artefact de fill)"],
 ["2","Gate two-sided","les deux directions contribuent (pas un beta directionnel déguisé)"],
 ["3","Gate DSR (Deflated Sharpe)","Sharpe significatif après déflation pour le multiple-testing de la grille"],
 ["4","Gate OOS (train≤2015 / test≥2016)","l'edge persiste hors-échantillon"],
 ["5","Audit mark-to-market + facteur","alpha couvert-beta significatif vs marché ET facteur tendance (TSMOM)"],
]
story += [kv_table(meth, [1.3*cm, 6.2*cm, 8.9*cm]),
          Spacer(1,5),
          Paragraph("Mesure de performance : série de rendements <b>quotidiens en mark-to-market réel</b> (close-to-close de "
                    "chaque position ouverte), et non un R étalé sur la détention — ce dernier sous-estime la volatilité et "
                    "gonfle artificiellement le Sharpe (correctif appliqué après l'audit d'une stratégie antérieure).", BODY)]
story += [PageBreak()]

# ---------------- 5. PERFORMANCE ----------------
story += [Paragraph("5. Analyse de performance", H1), hr()]
perf_rows = [
 ["Métrique","Portefeuille","Métrique","Portefeuille"],
 ["CAGR","+4,1 %","Trades (total / an)","5 947 / ~193"],
 ["Volatilité annualisée","4,2 %","Taux de réussite","44,4 %"],
 ["Sharpe ratio","0,98","Gain moy. / perte moy.","1,70"],
 ["Sortino ratio","1,42","Profit factor","1,36"],
 ["Calmar ratio","0,79","Espérance / trade","+0,043 R"],
 ["Meilleure année","2008 : +24 %","Détention moyenne","11,4 j"],
 ["Pire année","2000 : −5 %","Exposition (% long)","57 %"],
]
story += [kv_table(perf_rows, [4.2*cm,4.0*cm,4.2*cm,4.0*cm]),
          Spacer(1,8), Image(os.path.join(RES,"s076_fig_perf.png"), width=16.4*cm, height=10.1*cm),
          Paragraph("Fig. 1 — Courbe d'équité (vs buy&hold), drawdown, rendements annuels, Sharpe glissant 12 mois. "
                    "Performance positive sur 23 des 27 années ; gains marqués lors des crises 2008 (+24 %) et 2020 (+20 %) "
                    "→ convexité positive.", SMALL)]
story += [PageBreak()]

# ---------------- 6. RISK ----------------
story += [Paragraph("6. Analyse de risque", H1), hr()]
risk_rows = [
 ["Métrique de risque","Valeur","Lecture"],
 ["Max drawdown (MTM)","−5,2 %","faible ; le −79 % « trade-séquentiel » est un artefact de métrique"],
 ["Durée max de drawdown","~430 jours","principal point faible : longues phases plates"],
 ["VaR 95 % / CVaR 95 % (quotidien)","−0,36 % / −0,55 %","queues maîtrisées à l'échelle journalière"],
 ["Skew quotidien / par trade","+2,32 / +4,81","convexité positive : petites pertes, gros gains"],
 ["Kurtosis quotidienne","46,6","fat tails (côté droit) — gains extrêmes, pertes bornées (worst trade −1,0 R)"],
 ["Exposition / jours investis","99 % / 50 %","quasi toujours ≥1 position ; ~6 positions concurrentes"],
]
story += [kv_table(risk_rows, [4.6*cm,3.0*cm,8.8*cm]),
          Spacer(1,8), Image(os.path.join(RES,"s076_fig_risk.png"), width=16.4*cm, height=10.1*cm),
          Paragraph("Fig. 2 — Distribution des trades (asymétrie droite), Sharpe par classe, carte mensuelle des rendements, "
                    "positions concurrentes. Pertes plafonnées par les stops ; gains à queue épaisse (skew +4,8 par trade).", SMALL)]
story += [PageBreak()]

# ---------------- 7. ROBUSTNESS ----------------
story += [Paragraph("7. Robustesse & tests anti-artefact", H1), hr()]
rob = [
 ["Test","Résultat","Interprétation"],
 ["Causalité (troncature données)","0 trade modifié / 3 583","strictement causal : aucune fuite d'information future"],
 ["Robustesse délai d'entrée +2/+3/+5","Sharpe 1,49 / 1,58 / 1,68","ne s'effondre pas → pas de leak au bar d'entrée"],
 ["Placebo « acheter chaque plus-haut »","+0,024 R (vs +0,040)","fond = breakout-momentum ; le hook ajoute +40 %"],
 ["Alpha vs marché + TSMOM (12 m)","t = 5,6 ; corr 0,11","ni beta marché ni beta tendance"],
 ["Données FTMO réelles (indices+or+crypto)","Sharpe 0,70 ; alpha t = 4,0","edge confirmé hors données proxy"],
 ["Par classe (IC bootstrap 95 %)","indices/comm./crypto > 0","significatif ; FX non significatif (exclu)"],
 ["Sous-périodes 00-09 / 10-18 / 19-26","Sh couvert 1,06 / 0,93 / 1,05","stable, vivant en récent"],
 ["Stress coûts +0/+3/+6/+10 bps","Sh 1,58 → 1,09","dégradation douce, reste positif"],
 ["Contrôle négatif (SMA dual #80)","DISCARD (beta long)","la tendance générique échoue → l'edge vient de la sélectivité"],
]
story += [kv_table(rob, [5.6*cm,4.0*cm,6.8*cm])]

# ---------------- 8. RISK FACTORS ----------------
story += [Paragraph("8. Facteurs de risque & limites (à challenger)", H1), hr()]
for t_, d_ in [
 ("Proxy vs 1-2-3 littéral","Le moteur n'implémente pas la reconnaissance formelle du pattern 1-2-3 ; à coder pour confirmation."),
 ("Données commodités proxy","La part non-or repose sur des futures continus Yahoo → revalider sur données broker réelles."),
 ("Prime connue, non propriétaire","~60 % de l'edge = breakout-momentum générique ; risque de surpopulation/décroissance."),
 ("Durée de drawdown","~430 j de drawdown maximal : tolérance psychologique et capital patient requis."),
 ("Multiple testing","1 survivant sur 80 stratégies ; atténué par la stabilité multi-période et les données réelles, mais réel."),
 ("Effet lent","robuste à un délai de +5 j → le « hook » précis n'est pas critique ; simplifiable mais non différenciant."),
 ("Slippage des cassures","entrées sur stops de cassure → coût d'exécution réel à valider en paper-trading."),
]:
    story += [Paragraph(f"• <b>{t_}.</b> {d_}", BODY)]

# ---------------- 9. CONCLUSION ----------------
story += [Paragraph("9. Conclusion & recommandation", H1), hr(),
          Paragraph("Le Ross Hook présente un edge <b>réel, significatif et correctement isolé du beta</b>, avec un profil de "
                    "risque attrayant (Sharpe ~1,0, Calmar 0,79, DD −5 %, convexité positive). Il satisfait l'intégralité du "
                    "protocole de validation, ce qu'aucune des 79 autres stratégies n'a fait. Sa nature — prime de "
                    "breakout-momentum court terme bien implémentée — est honnêtement reconnue.", BODY),
          Paragraph("<b>Recommandation : approuver pour une phase de validation pré-déploiement</b> (paper-trading 3–6 mois) "
                    "sur le sleeve indices + commodités + crypto, en parallèle de : (i) ré-implémentation indépendante, "
                    "(ii) revalidation des commodités sur données broker réelles, (iii) test du 1-2-3 littéral, "
                    "(iv) étude de capacité/slippage. Allocation pilote conditionnée à ces vérifications.", BODY)]

# ---------------- APPENDIX ----------------
story += [Paragraph("Annexe — Paramètres & reproduction", H2),
          Paragraph("Paramètres : Min_Setup=10, Max_Hook=20, Time=10, ATR_Length=20, ATR_Stop=6, RISK_FRAC=0,5 %. "
                    "Reproduction : <font face='Courier'>python strat_s076_ross_hook.py</font> (gates) ; "
                    "<font face='Courier'>python s076_deepdive.py</font> (audit) ; "
                    "<font face='Courier'>python s076_causality.py</font> (look-ahead) ; "
                    "<font face='Courier'>python s076_report_analytics.py</font> (métriques & figures). "
                    "Code : code/rosshook.py. Spec détaillée : SPEC_S076_ross_hook.md. Dossier d'audit : AUDIT_DOSSIER_S076.md.", SMALL)]

def footer(canvas, doc):
    canvas.saveState(); canvas.setFont('Helvetica', 7); canvas.setFillColor(colors.HexColor('#888888'))
    canvas.drawString(2*cm, 1.1*cm, "Ross Hook (#76) — Rapport de due-diligence — Confidentiel / usage interne")
    canvas.drawRightString(19*cm, 1.1*cm, f"p. {doc.page}")
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2.3*cm, rightMargin=2.3*cm, topMargin=2*cm, bottomMargin=1.7*cm,
                        title="Ross Hook - Rapport institutionnel", author="oxfordstrat_109")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("PDF written:", OUT)
