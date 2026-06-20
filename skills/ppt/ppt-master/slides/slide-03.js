function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText("蓝联科技 — 商业数字化科技服务商", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addText("蓝联科技有限公司成立于2014年，", {
    x: 0.8, y: 1.3, w: 4.2, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addText("是国家级高新技术企业、广东省专精特新企业，", {
    x: 0.8, y: 1.6, w: 4.2, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addText("专注于商业地产数字化领域。", {
    x: 0.8, y: 1.9, w: 4.2, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addText("核心能力：", {
    x: 0.8, y: 2.25, w: 4.2, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei", color: theme.primary, bold: true, valign: "middle"
  });
  slide.addText("● AI智能应用：AI问数、AI客服、AI知识库、AI Skills工作流", {
    x: 0.8, y: 2.6, w: 4.2, h: 0.55,
    fontSize: 13, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addText("● 商圈会员CRM：集团级会员管理、积分营销、私域商城", {
    x: 0.8, y: 3.2, w: 4.2, h: 0.55,
    fontSize: 13, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addText("● 数字营销运营：联合运营、新媒体、活动企划", {
    x: 0.8, y: 3.8, w: 4.2, h: 0.35,
    fontSize: 13, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addText("服务覆盖购物中心、写字楼、产业园区、文旅商业等业态，", {
    x: 0.8, y: 4.2, w: 4.2, h: 0.25,
    fontSize: 13, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addText("在广州、深圳、南宁、福州等地服务超过30个商业项目。", {
    x: 0.8, y: 4.45, w: 4.2, h: 0.25,
    fontSize: 13, fontFace: "Microsoft YaHei", color: theme.secondary, valign: "top"
  });
  slide.addShape(pres.ShapeType.rect, {
    x: 5.4, y: 1.3, w: 4, h: 3.6, fill: { color: "f0f4f8" }, rectRadius: 0.1,
    shadow: { type: "outer", blur: 6, offset: 2, color: "000000", opacity: 0.1 }
  });
  slide.addText("30+", {
    x: 5.4, y: 1.6, w: 4, h: 1,
    fontSize: 48, fontFace: "Microsoft YaHei", color: theme.accent, bold: true, align: "center"
  });
  slide.addText("商业地产项目经验", {
    x: 5.4, y: 2.8, w: 4, h: 0.4,
    fontSize: 16, fontFace: "Microsoft YaHei", color: theme.secondary, align: "center"
  });
  slide.addShape(pres.ShapeType.rect, { x: 6.2, y: 3.4, w: 2.4, h: 0.02, fill: { color: theme.light } });
  slide.addText("国家级高新技术企业", {
    x: 5.4, y: 3.55, w: 4, h: 0.25,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary, align: "center"
  });
  slide.addText("广东省专精特新企业", {
    x: 5.4, y: 3.8, w: 4, h: 0.25,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary, align: "center"
  });
  slide.addText("ISO三体系认证", {
    x: 5.4, y: 4.05, w: 4, h: 0.25,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary, align: "center"
  });
  slide.addText("40+项软著 | 14项专利", {
    x: 5.4, y: 4.3, w: 4, h: 0.25,
    fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary, align: "center"
  });
  slide.addText("03", { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", color: "999999", align: "right" });
}
module.exports = { createSlide };
