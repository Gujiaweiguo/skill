var DEFAULT_PALETTE = {
  deep: "0F2338",
  deep2: "16324A",
  ink: "193346",
  inkSoft: "556B7B",
  line: "D9E2E8",
  white: "FFFFFF",
  paper: "F7F6F1",
  mist: "F5F8FA",
  blue: "1E5A8A",
  blueSoft: "E4F0FA",
  teal: "1E8C89",
  tealSoft: "DDF3F1",
  amber: "C9892B",
  amberSoft: "F8EFD9",
  coral: "D46B43",
  coralSoft: "F9E5DD",
  green: "4C8B5D",
  greenSoft: "E2F0E6",
  red: "BA5149",
  redSoft: "F7E0DE",
  purple: "7562A8",
  purpleSoft: "ECE8F7"
};

var TONES = {
  blue: { main: "blue", soft: "blueSoft" },
  teal: { main: "teal", soft: "tealSoft" },
  amber: { main: "amber", soft: "amberSoft" },
  coral: { main: "coral", soft: "coralSoft" },
  green: { main: "green", soft: "greenSoft" },
  red: { main: "red", soft: "redSoft" },
  purple: { main: "purple", soft: "purpleSoft" }
};

function createLayouts(pptx, paletteOverrides) {
  var C = {};
  var key;
  for (key in DEFAULT_PALETTE) {
    C[key] = DEFAULT_PALETTE[key];
  }
  if (paletteOverrides) {
    for (key in paletteOverrides) {
      C[key] = paletteOverrides[key];
    }
  }

  var W = 13.333;
  var H = 7.5;

  function addBg(slide, color) {
    slide.background = { color: color || C.white };
  }

  function addTopBand(slide, title, kicker, page, opts) {
    opts = opts || {};
    var footerText = opts.footerText || ("立项汇报  |  " + page);
    slide.addShape(pptx.ShapeType.rect, {
      x: 0, y: 0, w: W, h: 0.66,
      fill: { color: C.deep }
    });
    slide.addText(title, {
      x: 0.62, y: 0.88, w: 8.8, h: 0.46,
      fontFace: "Microsoft YaHei", fontSize: 24, bold: true, color: C.ink, margin: 0
    });
    if (kicker) {
      slide.addText(kicker, {
        x: 10.7, y: 0.93, w: 1.85, h: 0.32,
        fontFace: "Microsoft YaHei", fontSize: 10, bold: true,
        color: C.coral, align: "center", valign: "mid",
        fill: { color: C.white }, line: { color: C.coral, pt: 1.1 },
        radius: 0.1, margin: 0.02
      });
    }
    slide.addShape(pptx.ShapeType.line, {
      x: 0.62, y: 1.42, w: 12.05, h: 0,
      line: { color: C.line, pt: 1 }
    });
    slide.addText(footerText, {
      x: 10.7, y: 7.03, w: 1.85, h: 0.2,
      fontFace: "Microsoft YaHei", fontSize: 9,
      color: C.inkSoft, align: "right", margin: 0
    });
  }

  function addSectionLabel(slide, x, y, w, text, tone) {
    tone = tone || "blue";
    var colorName = TONES[tone] ? TONES[tone].main : "blue";
    var softName = TONES[tone] ? TONES[tone].soft : "blueSoft";
    slide.addText(text, {
      x: x, y: y, w: w, h: 0.26,
      fontFace: "Microsoft YaHei", fontSize: 10, bold: true,
      color: C[colorName], align: "center", valign: "mid",
      fill: { color: C[softName] }, line: { color: C[colorName], pt: 1 },
      radius: 0.08, margin: 0.02
    });
  }

  function addCard(slide, cfg) {
    var fill = cfg.fill || C.white;
    var line = cfg.line || C.line;
    var accent = cfg.accent || C.blue;
    var titleSize = cfg.titleSize || 16;
    var bodySize = cfg.bodySize || 11.5;
    slide.addShape(pptx.ShapeType.roundRect, {
      x: cfg.x, y: cfg.y, w: cfg.w, h: cfg.h,
      rectRadius: 0.08, line: { color: line, pt: 1.1 }, fill: { color: fill }
    });
    slide.addShape(pptx.ShapeType.rect, {
      x: cfg.x, y: cfg.y, w: 0.1, h: cfg.h,
      fill: { color: accent }
    });
    slide.addText(cfg.title, {
      x: cfg.x + 0.22, y: cfg.y + 0.16, w: cfg.w - 0.34, h: 0.28,
      fontFace: "Microsoft YaHei", fontSize: titleSize, bold: true,
      color: C.ink, margin: 0
    });
    if (Array.isArray(cfg.body)) {
      cfg.body.forEach(function (item, idx) {
        var top = cfg.y + 0.58 + idx * 0.34;
        slide.addShape(pptx.ShapeType.ellipse, {
          x: cfg.x + 0.24, y: top + 0.08, w: 0.06, h: 0.06,
          fill: { color: accent }
        });
        slide.addText(item, {
          x: cfg.x + 0.36, y: top, w: cfg.w - 0.52, h: 0.22,
          fontFace: "Microsoft YaHei", fontSize: bodySize,
          color: C.inkSoft, margin: 0
        });
      });
    } else {
      slide.addText(cfg.body, {
        x: cfg.x + 0.22, y: cfg.y + 0.54, w: cfg.w - 0.38, h: cfg.h - 0.7,
        fontFace: "Microsoft YaHei", fontSize: bodySize,
        color: C.inkSoft, margin: 0, valign: "top"
      });
    }
  }

  function addMetricCard(slide, x, y, w, h, tone, num, title, desc) {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: x, y: y, w: w, h: h,
      rectRadius: 0.08, line: { color: tone.soft, pt: 1 },
      fill: { color: tone.bg }
    });
    slide.addText(num, {
      x: x + 0.2, y: y + 0.18, w: w - 0.3, h: 0.36,
      fontFace: "Microsoft YaHei", fontSize: 24, bold: true,
      color: tone.main, margin: 0
    });
    slide.addText(title, {
      x: x + 0.2, y: y + 0.72, w: w - 0.3, h: 0.22,
      fontFace: "Microsoft YaHei", fontSize: 14, bold: true,
      color: C.ink, margin: 0
    });
    slide.addText(desc, {
      x: x + 0.2, y: y + 1.02, w: w - 0.3, h: 0.44,
      fontFace: "Microsoft YaHei", fontSize: 10.5,
      color: C.inkSoft, margin: 0
    });
    slide.addShape(pptx.ShapeType.line, {
      x: x + 0.2, y: y + 0.64, w: w - 0.4, h: 0,
      line: { color: tone.soft, pt: 1 }
    });
  }

  function addBulletList(slide, items, x, y, w, opts) {
    opts = opts || {};
    var gap = opts.gap || 0.46;
    var fontSize = opts.fontSize || 14;
    var color = opts.color || C.ink;
    var bullet = opts.bullet || C.coral;
    items.forEach(function (item, i) {
      var top = y + i * gap;
      slide.addShape(pptx.ShapeType.ellipse, {
        x: x, y: top + 0.1, w: 0.08, h: 0.08,
        fill: { color: bullet }
      });
      slide.addText(item, {
        x: x + 0.16, y: top, w: w, h: 0.24,
        fontFace: "Microsoft YaHei", fontSize: fontSize,
        color: color, margin: 0
      });
    });
  }

  function addFlowDiagram(slide, cfg) {
    var tone = cfg.tone || C.blue;
    var soft = cfg.soft || C.blueSoft;
    var footerTags = cfg.footerTags || [];
    slide.addShape(pptx.ShapeType.roundRect, {
      x: cfg.x, y: cfg.y, w: cfg.w, h: cfg.h,
      rectRadius: 0.08, line: { color: C.line, pt: 1.1 },
      fill: { color: C.mist }
    });
    slide.addText(cfg.title, {
      x: cfg.x + 0.24, y: cfg.y + 0.18, w: cfg.w - 0.48, h: 0.26,
      fontFace: "Microsoft YaHei", fontSize: 16, bold: true,
      color: C.ink, margin: 0
    });
    var innerX = cfg.x + 0.22;
    var innerY = cfg.y + 0.72;
    var boxW = 0.96;
    var gap = 0.08;
    cfg.steps.forEach(function (step, idx) {
      var sx = innerX + idx * (boxW + gap);
      slide.addShape(pptx.ShapeType.roundRect, {
        x: sx, y: innerY, w: boxW, h: 2.08,
        rectRadius: 0.06, line: { color: tone, pt: 1 },
        fill: { color: C.white }
      });
      slide.addShape(pptx.ShapeType.ellipse, {
        x: sx + 0.25, y: innerY + 0.18, w: 0.46, h: 0.46,
        line: { color: soft, pt: 1 }, fill: { color: soft }
      });
      slide.addText(step.icon, {
        x: sx + 0.35, y: innerY + 0.28, w: 0.25, h: 0.16,
        fontFace: "Microsoft YaHei", fontSize: 12, bold: true,
        color: tone, align: "center", margin: 0
      });
      slide.addText(String(idx + 1), {
        x: sx + 0.08, y: innerY + 0.14, w: 0.18, h: 0.16,
        fontFace: "Microsoft YaHei", fontSize: 10, bold: true,
        color: tone, margin: 0
      });
      slide.addText(step.title, {
        x: sx + 0.08, y: innerY + 0.82, w: boxW - 0.16, h: 0.36,
        fontFace: "Microsoft YaHei", fontSize: 11, bold: true,
        color: C.ink, align: "center", margin: 0
      });
      slide.addText(step.desc, {
        x: sx + 0.06, y: innerY + 1.24, w: boxW - 0.12, h: 0.6,
        fontFace: "Microsoft YaHei", fontSize: 8.5,
        color: C.inkSoft, align: "center", valign: "mid", margin: 0
      });
      if (idx < cfg.steps.length - 1) {
        slide.addShape(pptx.ShapeType.chevron, {
          x: sx + boxW + 0.015, y: innerY + 0.88, w: 0.12, h: 0.28,
          fill: { color: tone }
        });
      }
    });
    var toneKey = tone === C.blue ? "blue" : tone === C.teal ? "teal" : tone === C.amber ? "amber" : tone === C.coral ? "coral" : "blue";
    footerTags.forEach(function (tag, idx) {
      addSectionLabel(slide, cfg.x + 0.24 + idx * 1.3, cfg.y + cfg.h - 0.42, 1.12, tag, toneKey);
    });
  }

  function addThreeExplainCards(slide, cfg) {
    cfg.cards.forEach(function (card, idx) {
      addCard(slide, {
        x: cfg.x, y: cfg.y + idx * (cfg.cardH + 0.18), w: cfg.w, h: cfg.cardH,
        title: card.title, body: card.body,
        fill: C.white, line: C.line, accent: cfg.accent,
        titleSize: 15, bodySize: 11
      });
    });
  }

  function addBottomStatement(slide, text, tone) {
    tone = tone || "blue";
    var colorName = TONES[tone] ? TONES[tone].main : "blue";
    var softName = TONES[tone] ? TONES[tone].soft : "blueSoft";
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.7, y: 6.36, w: 11.95, h: 0.42,
      rectRadius: 0.06, line: { color: C[colorName], pt: 1 },
      fill: { color: C[softName] }
    });
    slide.addText(text, {
      x: 0.96, y: 6.47, w: 11.45, h: 0.18,
      fontFace: "Microsoft YaHei", fontSize: 12, bold: true,
      color: C[colorName], align: "center", margin: 0
    });
  }

  function finishSlide() {}

  return {
    W: W, H: H, C: C,
    addBg: addBg,
    addTopBand: addTopBand,
    addSectionLabel: addSectionLabel,
    addCard: addCard,
    addMetricCard: addMetricCard,
    addBulletList: addBulletList,
    addFlowDiagram: addFlowDiagram,
    addThreeExplainCards: addThreeExplainCards,
    addBottomStatement: addBottomStatement,
    finishSlide: finishSlide
  };
}

module.exports = { createLayouts: createLayouts, DEFAULT_PALETTE: DEFAULT_PALETTE };
