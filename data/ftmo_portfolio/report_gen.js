const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, TableOfContents, HeadingLevel, BorderStyle,
        WidthType, ShadingType, Header, Footer, PageNumber, PageBreak } = require("docx");

const W = 9360;
const bd = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: bd, bottom: bd, left: bd, right: bd };
const cellm = { top: 60, bottom: 60, left: 100, right: 100 };

function p(text, opts = {}) {
  return new Paragraph({ spacing: { after: 120 }, ...opts.par,
    children: [new TextRun({ text, size: 21, ...opts })] });
}
function pr(runs, parOpts = {}) {
  return new Paragraph({ spacing: { after: 120 }, ...parOpts,
    children: runs.map(r => new TextRun({ size: 21, ...r })) });
}
function h1(t) { return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] }); }
function h2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] }); }
function bullet(t) {
  return new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 80 },
    children: [new TextRun({ text: t, size: 21 })] });
}
function cell(t, w, opts = {}) {
  return new TableCell({ borders, width: { size: w, type: WidthType.DXA }, margins: cellm,
    shading: opts.head ? { fill: "1F3B57", type: ShadingType.CLEAR } :
             (opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined),
    children: [new Paragraph({ children: [new TextRun({ text: String(t), size: 19,
      bold: !!opts.head, color: opts.head ? "FFFFFF" : undefined })] })] });
}
function table(widths, rows) {
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({ children: r.map((c, j) =>
      cell(c, widths[j], i === 0 ? { head: true } : {})) })) });
}
function pb() { return new Paragraph({ children: [new PageBreak()] }); }

const cover = [
  new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "PROGRAMME FTMO — RAPPORT INSTITUTIONNEL", size: 44, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 },
    children: [new TextRun({ text: "« Sprint pour passer, prudence pour durer »", size: 26, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "Version 2.0 — RÉVISION PRÉ-LANCEMENT — specs gelées, chiffres recalculés post-revue MD, checklist GO/NO-GO", size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 2000 },
    children: [new TextRun({ text: "10 juin 2026 — Quantitative Strategy Group", size: 20 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Diffusion équipe. Backtest + validation broker démo — 0 jour live. Test overnight empirique en cours.", size: 18, color: "888888" })] }),
  pb(),
  h1("Table des matières"),
  new TableOfContents("TOC", { hyperlink: true, headingStyleRange: "1-2" }),
  pb(),
];

const s1 = [
  h1("1. Résumé exécutif"),
  p("Deux portefeuilles systématiques sur l'univers FTMO ($10k, 2-Step, Swing) : CHALLENGE (machine de variance séquencée, maximise l'EV du passage sous horloge 3 mois) et FUNDED (même book de signaux, réglage rente, maximise l'extraction sous contrainte de longévité). Cette v2.0 intègre la revue MD sur compte démo réel : swaps mesurés au terminal (modèle confirmé à 1-10% près sur chaque jambe), marge réelle indices/or 1:50 (cap de marge 60% ajouté à la spec), et chiffres contractuels recalculés sur le stack corrigé."),
  table([3744, 1872, 1872, 1872], [
    ["Métrique clé (corrigée post-revue)", "IS 2013-19", "OOS 2020-26", "Note"],
    ["p(funded ≤ 3 mois, retries)", "87.1%", "79.9%", "design gelé sur IS"],
    ["Pooled (n=462)", "83.5% — IC95 [76.2 ; 88.5]", "P(p>50%) = 1.00", "step 7"],
    ["EV par campagne", "+$953", "+$825", "EV chaînée ≈ +$800"],
    ["Temps médian de funding", "~32 j", "~34 j", "1 essai possible en 13 j (replay avril)"],
    ["Extraction Funded 2 ans (brut)", "$824", "$2,592", "bust 1-2%, 10.8 payouts OOS"],
  ]),
  p(""),
  pr([{ text: "Robustesse : ", bold: true },
      { text: "triangulation moteur/renouvellement 1.8 pt d'écart ; bootstrap 78 histoires synthétiques : P(p>50%) = 100%, pire 62.9% ; stress swap ×1.5 → 86.4%, spread ×2 → 77.2% ; antifragile au slippage breaker (p monte, coût −$30-60 EV) ; placebo : container ~71 pts + edge réel +12 pts ; aucun look-ahead (anticausal négatif)." }]),
  pr([{ text: "Replay grandeur nature (anecdote, pas statistique) : ", bold: true },
      { text: "lancé le 10 avril 2026, le funnel aurait été FUNDED le 23 avril — 1 essai, 13 jours. Le compte funded serait à −0.85% au 5 juin (mai = régime ORB défavorable, prévu par le nowcast d'archive), jamais en danger (min $9,829 vs floor $9,000)." }]),
];

const s2 = [
  pb(), h1("2. Les deux portefeuilles (spécifications gelées v2)"),
  h2("2.1 Sleeves communs"),
  table([1900, 4200, 1630, 1630], [
    ["Sleeve", "Spécification (gelée, archive-validée)", "SR net full", "SR net 2019+"],
    ["Or trend", "TSMOM blend sign{60,120,250} carry-adj, θ=0.34, vol-target 10%, XAUUSD", "0.35", "0.47"],
    ["J1", "USDJPY TSMOM 12-1 long-only, vol-target 10%", "0.43", "0.42"],
    ["Overnight midweek", "Long US100+GER40, nuits lun & mar (17:35/22:05 → 09:00/15:30 CET), net swap+spread", "0.66", "0.46"],
    ["ORB V2+E7", "ORB 30min US100, ledger NQ 4013 trades, coût d'époque (auction mesurée/année)", "0.40", "0.99"],
  ]),
  p(""),
  h2("2.2 CHALLENGE (mur 3 mois)"),
  table([3120, 6240], [
    ["Paramètre", "Valeur gelée"],
    ["Vol multiplier", "14× (cap 1.5×/jambe pré-vm ; budgets or 0.5 / jpy 0.5 / overnight 0.6/jambe / ORB 0.25% tapéré)"],
    ["Phase 2", "1.2× le risque P1 (barrières +5/−10)"],
    ["Breaker / taper / pacing", "flatten M5 si room < 30% du budget daily ; taper floor 2% ; pacing ×[0.8;2.0] ; glide 0.5"],
    ["Abandon", "equity < floor+2% pendant 5 j → relancer (l'horloge continue)"],
    ["Cap de marge (NOUVEAU v2)", "Σ marge ≤ 60% equity (taux MESURÉS : indices/or 2% = 1:50, FX 1%) — scaling proportionnel. Sans cap : marge p99 = 93% = zone margin-call"],
    ["Exécution", "rebalance 22:05 CET ; quantization lots 0.01 ; weekend tenu ; P&L NON réalisé quotidiennement (buffer flottant)"],
  ]),
  p(""),
  h2("2.3 FUNDED (rente)"),
  table([3120, 6240], [
    ["Paramètre", "Valeur gelée"],
    ["Vol multiplier", "1.0× ; breaker 30%, taper 2% ; pace/glide/abandon OFF ; cap marge 60%"],
    ["Retraits", "bi-mensuels (balance − $10k si positif) ; split 80% ; 1er payout rembourse la fee"],
    ["Compte & switch", "Swing à l'achat (irréversible) ; switch vm 14 → 1.0 IMMÉDIAT au funding (book sprint gardé funded : méd. $0, 59% bust, 27 j — mesuré)"],
  ]),
];

const s3 = [
  pb(), h1("3. Métriques de validation (stack corrigé)"),
  h2("3.1 Challenge — funnel 91 jours"),
  table([3300, 2020, 2020, 2020], [
    ["Mesure", "IS", "OOS", "Note"],
    ["p(funded), retries+abandon", "87.1%", "79.9%", "essais 3.26 / 3.50"],
    ["EV campagne (fee $96, valeur funded $1,342)", "+$953", "+$825", ""],
    ["1 SEUL essai (61j)", "—", "28.2% max", "plafond structurel"],
    ["95% funded", "mur 270 j", "3.91 essais", ""],
    ["Stress swap ×1.5 / spread ×2 (pooled)", "86.4% / 77.2%", "+$940 / +$751", ""],
    ["Slippage breaker k=1.0", "85.2%", "+$767", "antifragile"],
  ]),
  p(""),
  h2("3.2 Funded — extraction 2 ans (tronquée, conservateur)"),
  table([3300, 2020, 2020, 2020], [
    ["Mesure", "IS", "OOS", "Note"],
    ["E[extraction brute]", "$824", "$2,592", "méd. OOS $2,145"],
    ["Bust / payouts / vie médiane", "2%", "1% / 10.8 / horizon plein", ""],
  ]),
  p(""),
  h2("3.3 Suite d'inférence"),
  table([3300, 3030, 3030], [
    ["Test", "Résultat", "Lecture"],
    ["Triangulation (renouvellement indépendant)", "79.0% vs 80.8%", "pas de bug moteur ; essais quasi indépendants"],
    ["Bootstrap chemins (78 histoires, blocs 13 sem.)", "p5 74.3%, min 62.9%", "P(p>50%) = 100%"],
    ["Placebo sign-flip / delay / anticausal", "71.4% vs 83.3% / −1.3 pt / pas d'amélioration", "edge réel +12 pts ; zéro look-ahead"],
  ]),
];

const s4 = [
  pb(), h1("4. Revue MD & validation broker (NOUVEAU v2)"),
  h2("4.1 La question des unités de swap — tranchée"),
  p("La revue MD signalait des swaps longs apparents de −385%/an (GER40) à −800%/an (US100). Résolution par les captures MT5 du compte démo : « Type de swap : En points », Chiffres = 2 → 1 point = 0.01 unité de cotation. Les pourcentages étaient la colonne points lue comme du %/an. Le modèle est confirmé par la mesure :"),
  table([1900, 1900, 1900, 1800, 1860], [
    ["Jambe", "MT5 mesuré (pts)", "Converti (bps/nuit)", "Modèle", "Écart"],
    ["US100 long", "−644.06", "−2.24", "−2.21", "+1.4%"],
    ["GER40 long", "−394.85", "−1.61", "−1.78 (estimé)", "−10% → mesuré intégré"],
    ["GER40 short", "−48.8", "−0.20", "+0.10 (estimé)", "signe corrigé"],
    ["XAUUSD long", "−89.26", "−2.06", "−2.03", "+1.5%"],
    ["USDJPY long", "+2.95", "+0.18", "+0.18", "exact"],
  ]),
  p("Triple-days confirmés (vendredi indices, mercredi métaux/FX). Annualisés : US100 −8.2%/an, GER40 −5.9%, XAU −7.5% — le swap est bien LE coût dominant du sleeve overnight (≈40% du gross), et il était déjà chargé."),
  h2("4.2 Découverte matérielle : marge indices/or = 2% (1:50)"),
  p("Les captures révèlent un taux de marge 2.0 sur US100/GER40 (et non 1% supposé). Au pic du sprint vm14, la marge requise atteignait p99 = 93% de l'equity — zone de margin-call après une mauvaise journée. Correctif : cap de marge dur à 60% de l'equity (scaling proportionnel des cibles). Impact mesuré : p 80.8 → 81.1%, EV +$838 — une contrainte de faisabilité gratuite, désormais dans la spec gelée."),
  h2("4.3 Test empirique overnight (EN COURS — dernier verrou)"),
  p("Positions tenues cette nuit sur le compte démo par le MD. Prédictions falsifiables du modèle (nuit 1×) :"),
  table([2800, 2200, 2180, 2180], [
    ["Ordre", "Swap prédit (modèle)", "Si lecture %/an", "Verdict si"],
    ["BUY 0.10 lot US100.cash", "−$0.64", "≈ −$50", "facteur 80 d'écart"],
    ["BUY 0.10 lot GER40.cash", "−€0.39", "≈ −$26", "illisible de se tromper"],
    ["BUY 0.01 lot XAUUSD", "−$0.89", "≈ −$10.7", ""],
    ["BUY 0.01 lot USDJPY", "+$0.02", "—", ""],
  ]),
  p("Nuit 2 recommandée : mercredi (XAU ×3 → −$2.68 attendu, indices ×1) ou vendredi (indices ×3 → US100 −$1.93) pour valider le calendrier des triple-days."),
  h2("4.4 Replay grandeur nature : avril → juin 2026"),
  table([3120, 6240], [
    ["Étape", "Résultat"],
    ["Challenge lancé 10 avril", "P1 passée en 4 j de trading (pic $11,162) ; P2 en 4 j ($10,554)"],
    ["FUNDED 23 avril", "1 essai, 13 jours calendaires, $96 de fee (~25% de proba de premier-coup : tirage favorable, pas exceptionnel)"],
    ["Funded 28 avr → 5 juin (vm 1.0)", "equity $9,915 (−0.85%), min $9,829 (9.2% au-dessus du floor), 0 danger. Attribution : or 0% (zone morte), J1 +0.24%, overnight +0.41%, ORB −1.47% (mai = régime défavorable ORB, prévu par le nowcast d'archive)"],
    ["Lecture", "le funnel fait ce que la simulation promet (vite quand le tirage est bon) ; la rente fait ce qu'elle promet (survivre aux mois plats). Un chemin = une anecdote ; les 462 cohortes restent la preuve"],
  ]),
];

const s5 = [
  pb(), h1("5. Données, coûts, architecture"),
  h2("5.1 Sources & réparations (audit F1)"),
  bullet("M1 true-UTC ×28 instruments (Dukascopy+MT5, 2007-2026, spreads calibrés) ; NQ databento 2010-2026 ; panels daily 2000+ ; rates 3m ×10 devises ; specs broker + captures MT5 2026-06."),
  bullet("Réparations : US100 2018-2020 (1 bar/jour → breaker aveugle, +9.2 pts IS fictifs) comblé par proxy NQ ; GER40 mi-2019→2021 masqué ; realized_vol min_periods (les NaN de calendrier zérotaient les poids 60 j post-férié)."),
  bullet("Stack unique : audit_stack.load_audited() — swaps ré-ancrés sur les valeurs MESURÉES (4.1). Toute analyse hors de ce loader est non conforme."),
  h2("5.2 Coûts (L33)"),
  table([1900, 2400, 5060], [
    ["Classe", "RT all-in mesuré", "Swap (calibré + mesuré, variable via taux 3m)"],
    ["FX majors", "1.1-3.1 bps", "markups 1.4-3.5%/an ; USDJPY long = crédit"],
    ["Indices", "2.2 bps (auction 0.5 bps actuel ; 4.3 en 2013 → ORB era-costed)", "US100 −2.24 bps/nuit MESURÉ ; GER40 −1.61 MESURÉ"],
    ["XAU", "1.8 bps", "−2.06 bps/nuit MESURÉ ; mercredi ×3"],
    ["Crypto / softs", "18.5 / 144-1190 bps", "−30%/an / exclus"],
  ]),
  h2("5.3 Simulateur (fidélité règles officielles 2026)"),
  bullet("Daily limit : equity ≥ balance@00:00 CE(S)T − 5% initial, vérifié M5 ; floor statique $9k ; cibles balance positions closes ; min 4 jours d'ouverture ; gap inter-phases 3 j ouvrés, retry 2 j ; évaluation sans restriction news/weekend (officiel)."),
  bullet("Comptabilité : avg-price, P&L réalisé sur réductions, swaps minuit (3× mer/ven selon classe), quantization lots, cap marge 60%, breaker avec stress de slippage ±k×range."),
];

const s6 = [
  pb(), h1("6. Reproduction & tests de non-régression"),
  table([700, 4660, 4000], [
    ["#", "Commande (ftmo_portfolio/)", "Valeur attendue (±1.5 pt cohortes / ±10% montants)"],
    ["1", "python3 dataio.py", "caches daily CET + M5, 28 instruments"],
    ["2", "python3 research_panel.py && python3 run_phase0.py", "RT: EURUSD 1.13 / US100 2.20 / BTC 18.50 bps ; swap US100 = −$6.44/lot/nuit"],
    ["3", "python3 prep_signals.py && python3 fix_overnight.py", "or actif 42% ; US100 all-nights +3.45 bps (t=2.1)"],
    ["4", "python3 repair_data.py + re-cost ORB", "967 jours comblés ; orb era-cost full ≈ 0.000 / 2021+ +0.099"],
    ["5", "funnel challenge (cfg gelée §2.2, margin_cap=0.60)", "IS 87.1% / OOS 79.9% / pooled 83.5%"],
    ["6", "funded vm1.0 wd14", "OOS $2,592 ±10%"],
    ["7", "path_bootstrap.py ×4 seeds", "p moyen ~84.8, min >60%"],
  ]),
  p(""),
  bullet("Non-régression : anticausal −1j ne doit JAMAIS améliorer (>+1 pt = leak) ; placebo book-vs-flip ≈ +10-14 pts ; ancres de coûts (US100 −$6.44/nuit, auction 0.5 bps) à ±20% ; couverture intraday ≥100 bars/jour/instrument/année."),
];

const s7 = [
  pb(), h1("7. Checklist de lancement GO/NO-GO"),
  table([4680, 1560, 3120], [
    ["Gate", "Statut", "Critère"],
    ["Specs gelées + chiffres contractuels recalculés", "FAIT", "v2.0 (ce document)"],
    ["Audit data/causalité/comptabilité + triangulation + bootstrap", "FAIT", "AUDIT.md, §3.3"],
    ["Swaps validés au terminal (captures MT5)", "FAIT", "modèle ±10% (§4.1)"],
    ["Cap de marge (taux 1:50 mesuré)", "FAIT", "60% equity, dans la spec"],
    ["Test overnight empirique (positions réelles)", "EN COURS", "swap observé = prédiction ±20% ; sinon STOP + re-cost"],
    ["Démo 3 semaines : spread auction ≤1.5 bps all-in ; slippage breaker ; swaps ±50%", "À FAIRE", "kill : auction >1.5 bps → ORB off"],
    ["EA MT5 (rebalance 22:05, breaker M5, abandon J+5) + réconciliation quotidienne", "À FAIRE", "écarts inexpliqués 3 j → STOP"],
    ["Budget : 4+ fees d'avance (~$400) ; achat compte SWING", "À FAIRE", "irréversible Standard→Swing"],
    ["Acceptation du risque clause 7.3 (style agressif) — décision comité", "À DÉCIDER", "repli vm 12 ≈ −3 pts si discrétion requise"],
  ]),
  p(""),
  pr([{ text: "Règle de décision proposée : ", bold: true },
      { text: "GO si le test overnight confirme (±20%) ET la démo 3 semaines ne déclenche aucun kill-criterion. Tout échec d'un gate = retour au desk, pas de lancement partiel." }]),
];

const s8 = [
  pb(), h1("8. Cimetière des falsifications & leçons (à ne pas re-tester sans donnée nouvelle)"),
  table([2800, 3280, 3280], [
    ["Famille", "Verdict & preuve", "Note"],
    ["FX trend 10 paires / FX intraday (Tokyo fix, London fix, asian breakout, London momentum)", "morts (post-fix, IS/OOS)", "J1 seul survivant FX"],
    ["FX sessions (Ranaldo)", "edge RÉEL (t≈4 OOS, SR 1.5-1.7 coût zéro) mais break-even ~1 bps < spread retail", "test démo transmis (≤1.0 bps à 00:05/08:00)"],
    ["Softs/énergie/NGAS trend ; énergie carry", "morts au coût mesuré ; carry non testable (swap snapshot)", "le +0.55 initial = bug realized_vol, corrigé"],
    ["BTC trend LO (4 familles)", "DSR full 0.989 (réel jadis) mais 2022+ ≈ 0.3, funnel OOS −$6", "lead funding-rate (≥5 ans de données)"],
    ["Breakouts indices ×8 ; meta-label ORB F1", "artefact de fill ; look-ahead (bughunt archive)", "hérités"],
    ["Vol-governor, start-gate, VIX-skip, P2 froide, daily-realize, weekend-flat", "falsifiés en cohortes", "inversions mesurées"],
  ]),
  p(""),
  bullet("L-mesure-avant-verdict — l'ORB mort sur hypothèse, ressuscité sur mesure ; le « tailwind » swap de J1 mort sur mesure ; les −800%/an morts sur capture. Dans tous les sens."),
  bullet("L-data-blind-rules — un trou de granularité rend les règles de risque aveugles (busts non détectés = pass fictifs)."),
  bullet("L-variance-vs-drift — sous (barrière, horloge, retries), maximiser p(franchir) ≠ maximiser le Sharpe."),
  bullet("L-zombie / L-retry-paradox / L-buffer-flottant — les politiques de protection ont des effets de second ordre mesurables et souvent inversés."),
  p(""),
  p("Sources : PORTFOLIOS.md (specs + addenda), AUDIT.md, REPORT.md, FTMO_CANONICAL_STATE.md. Backlog : harnais de réconciliation live, gel YAML, funding-rate BTC (≥5 ans), FX sessions raw-spread, swaps historiques énergie.", { italics: true }),
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: "1F3B57" },
        paragraph: { spacing: { before: 280, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "2E5A7E" },
        paragraph: { spacing: { before: 220, after: 140 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "FTMO — Rapport institutionnel v2.0 (pré-lancement) — confidentiel équipe", size: 16, color: "999999" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Page ", size: 16 }), new TextRun({ children: [PageNumber.CURRENT], size: 16 })] })] }) },
    children: [...cover, ...s1, ...s2, ...s3, ...s4, ...s5, ...s6, ...s7, ...s8],
  }],
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync("RAPPORT_INSTITUTIONNEL_FTMO_v2.docx", b); console.log("written", b.length); });
