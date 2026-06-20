function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText("资质与荣誉", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  const certs = [
    "国家级高新技术企业",
    "广东省专精特新企业",
    "广东省创新型中小企业",
    "ISO9001 / ISO27001 / ISO20000 三体系认证",
    "累计取得 40+ 项软件著作权",
    "累计取得 14 项专利（含6项发明专利）",
    "超过 30 个商业地产数字化项目经验"
  ];
  certs.forEach((cert, i) => {
    const y = 1.5 + i * 0.5;
    slide.addShape(pres.ShapeType.rect, { x: 0.8, y: y + 0.1, w: 0.25, h: 0.25, fill: { color: theme.accent }, rectRadius: 0.03 });
    slide.addText("✓", { x: 0.8, y: y + 0.08, w: 0.25, h: 0.25, fontSize: 12, color: "ffffff", align: "center", valign: "middle" });
    slide.addText(cert, {
      x: 1.2, y: y, w: 7.5, h: 0.45,
      fontSize: 15, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "middle"
    });
  });
  slide.addText("04", { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", color: "999999", align: "right" });
}
module.exports = { createSlide };
