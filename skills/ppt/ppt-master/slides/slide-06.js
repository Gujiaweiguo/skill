function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText("国家战略：国企必须拥抱AI", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addShape(pres.ShapeType.rect, {
    x: 0.8, y: 1.4, w: 4.2, h: 3.5, fill: { color: "f0f7ff" }, rectRadius: 0.1
  });
  slide.addText("2025年2月", {
    x: 1, y: 1.6, w: 3.8, h: 0.4,
    fontSize: 16, fontFace: "Microsoft YaHei", color: theme.accent, bold: true
  });
  slide.addText('国资委"AI+"专项行动', {
    x: 1, y: 2.0, w: 3.8, h: 0.4,
    fontSize: 16, fontFace: "Microsoft YaHei", color: theme.accent, bold: true
  });
  var policies = [
    "战略定位：发展AI作为\"十五五\"规划重点",
    "算力基座：夯实AI基础设施",
    "数据突破：构建重点行业数据集",
    "场景赋能：推动AI规模化落地"
  ];
  policies.forEach(function(p, i) {
    slide.addText("▸ " + p, {
      x: 1, y: 2.6 + i * 0.45, w: 3.8, h: 0.4,
      fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary
    });
  });
  slide.addShape(pres.ShapeType.rect, {
    x: 5.2, y: 1.4, w: 4.2, h: 3.5, fill: { color: "fff8e1" }, rectRadius: 0.1
  });
  slide.addText("2025年8月", {
    x: 5.4, y: 1.6, w: 3.8, h: 0.4,
    fontSize: 16, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addText("国务院《人工智能+行动》", {
    x: 5.4, y: 2.0, w: 3.8, h: 0.4,
    fontSize: 16, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addText("目标到2027年：", {
    x: 5.4, y: 2.5, w: 3.8, h: 0.35,
    fontSize: 13, fontFace: "Microsoft YaHei", color: theme.secondary, bold: true
  });
  slide.addText("AI与重点领域深度融合", {
    x: 5.4, y: 2.9, w: 3.8, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary
  });
  slide.addText("智能终端、智能体应用普及率超70%", {
    x: 5.4, y: 3.2, w: 3.8, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary
  });
  slide.addText("智能经济核心产业规模快速增长", {
    x: 5.4, y: 3.5, w: 3.8, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary
  });
  slide.addText('\u201C十五五\u201D期间：深化拓展\u201CAI+\u201D专项行动', {
    x: 5.4, y: 3.8, w: 3.8, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary
  });
  slide.addText("推动人工智能与传统产业全链条深度融合", {
    x: 5.4, y: 4.1, w: 3.8, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary
  });
  slide.addText("06", { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", color: "999999", align: "right" });
}
module.exports = { createSlide };
