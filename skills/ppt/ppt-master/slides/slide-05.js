function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText("服务客户（部分）", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addText("超过30个商业地产项目经验，客户覆盖国企、上市企业、商业地产龙头企业", {
    x: 0.8, y: 1.3, w: 8.4, h: 0.4,
    fontSize: 12, fontFace: "Microsoft YaHei", color: "888888"
  });
  const clients = [
    { name: "广州城投商业", desc: "国企 | 300万㎡ | 大会员+联合运营" },
    { name: "粤海天河城", desc: "省属国企 | 广州地标 | 智慧商业平台" },
    { name: "白云国资", desc: "区属国企 | 社区商业 | 联合运营" },
    { name: "宝能集团", desc: "上市企业 | 7个项目 | 商业服务平台" },
    { name: "岁宝百货", desc: "连锁百强 | 私域商城 | 联合运营" },
    { name: "富康城集团", desc: "多业态集团 | 会员商城平台" },
    { name: "彩生活服务集团", desc: "全球最大社区平台 | 智慧社区" },
    { name: "长隆旅游集团", desc: "中国文旅龙头 | 会员品牌" },
    { name: "特区建发", desc: "深圳国企 | 136万㎡ | 园区运营" }
  ];
  const cols = 3, colW = 2.6, colH = 0.95, gapX = 0.3, gapY = 0.15;
  const startX = 0.8, startY = 1.8;
  clients.forEach((c, i) => {
    const col = i % cols, row = Math.floor(i / cols);
    const x = startX + col * (colW + gapX);
    const y = startY + row * (colH + gapY);
    const isStateOwned = c.desc.includes("国企");
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: y, w: colW, h: colH,
      fill: { color: isStateOwned ? "f0f7ff" : "f8f9fa" },
      rectRadius: 0.08,
      shadow: { type: "outer", blur: 3, offset: 1, color: "000000", opacity: 0.06 }
    });
    slide.addText(c.name, {
      x: x + 0.15, y: y + 0.1, w: colW - 0.3, h: 0.45,
      fontSize: 14, fontFace: "Microsoft YaHei", color: theme.primary, bold: true, valign: "middle"
    });
    slide.addText(c.desc, {
      x: x + 0.15, y: y + 0.55, w: colW - 0.3, h: 0.4,
      fontSize: 10, fontFace: "Microsoft YaHei", color: "777777", valign: "top"
    });
  });
  slide.addText("05", { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", color: "999999", align: "right" });
}
module.exports = { createSlide };
