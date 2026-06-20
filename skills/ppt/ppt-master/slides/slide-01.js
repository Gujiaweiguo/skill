function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };
  slide.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("蓝联科技有限公司", {
    x: 1, y: 1.2, w: 8, h: 1.2,
    fontSize: 40, fontFace: "Microsoft YaHei", color: "ffffff", bold: true, align: "center"
  });
  slide.addText("AI赋能国企数字化转型", {
    x: 1, y: 2.5, w: 8, h: 0.8,
    fontSize: 28, fontFace: "Microsoft YaHei", color: theme.light, align: "center"
  });
  slide.addShape(pres.ShapeType.rect, { x: 3.5, y: 3.5, w: 3, h: 0.04, fill: { color: theme.accent } });
  slide.addText("广州海港地产经营管理有限公司 | 2026年6月", {
    x: 1, y: 3.8, w: 8, h: 0.6,
    fontSize: 16, fontFace: "Microsoft YaHei", color: "999999", align: "center"
  });
  slide.addShape(pres.ShapeType.rect, { x: 0, y: 5.565, w: 10, h: 0.06, fill: { color: theme.accent } });
}
module.exports = { createSlide };
