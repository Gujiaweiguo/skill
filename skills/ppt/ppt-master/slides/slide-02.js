function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText("目录", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.8,
    fontSize: 30, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.2, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  const items = [
    "关于蓝联",
    "国企AI政策解读",
    "AI核心产品",
    "商管与会员能力",
    "国企与广州本地案例",
    "合作展望"
  ];
  items.forEach((item, i) => {
    const y = 1.6 + i * 0.6;
    slide.addText(String(i + 1), {
      x: 0.8, y: y, w: 0.5, h: 0.5,
      fontSize: 18, fontFace: "Microsoft YaHei", color: "ffffff", bold: true, align: "center", valign: "middle",
      fill: { color: theme.accent }, rectRadius: 0.05
    });
    slide.addText(item, {
      x: 1.5, y: y, w: 7, h: 0.5,
      fontSize: 18, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "middle"
    });
  });
  slide.addText("02", {
    x: 9, y: 5.15, w: 0.8, h: 0.3,
    fontSize: 10, fontFace: "Microsoft YaHei", color: "999999", align: "right"
  });
}
module.exports = { createSlide };
