function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText("AI对国企商业地产的三大价值", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: "Microsoft YaHei", color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  var values = [
    { icon: "⚡", title: "降本提效", lines: ["AI替代重复性人工", "智能问数无需IT排期", "工单处理自动化", "释放30%+运营人力"], color: theme.accent },
    { icon: "🛡️", title: "合规与风控", lines: ["AI全流程留痕", "数据可追溯", "满足国资监管", "\"实时、穿透、智慧\"要求"], color: theme.primary },
    { icon: "🎯", title: "服务升级", lines: ["7×24小时AI客服", "AI招商助手", "智能巡更", "提升租户与消费者体验"], color: theme.light }
  ];
  values.forEach(function(v, i) {
    var x = 0.8 + i * 3.05;
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: 1.5, w: 2.75, h: 3.5, fill: { color: "ffffff" }, rectRadius: 0.1,
      shadow: { type: "outer", blur: 6, offset: 2, color: "000000", opacity: 0.08 },
      line: { color: v.color, width: 1.5 }
    });
    slide.addText(v.icon, {
      x: x, y: 1.7, w: 2.75, h: 0.8,
      fontSize: 36, align: "center"
    });
    slide.addText(v.title, {
      x: x + 0.2, y: 2.5, w: 2.35, h: 0.5,
      fontSize: 18, fontFace: "Microsoft YaHei", color: theme.primary, bold: true, align: "center"
    });
    slide.addShape(pres.ShapeType.rect, { x: x + 0.8, y: 3.05, w: 1.15, h: 0.03, fill: { color: v.color } });
    v.lines.forEach(function(line, li) {
      slide.addText(line, {
        x: x + 0.2, y: 3.2 + li * 0.35, w: 2.35, h: 0.3,
        fontSize: 12, fontFace: "Microsoft YaHei", color: theme.secondary, align: "center"
      });
    });
  });
  slide.addText("07", { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", color: "999999", align: "right" });
}
module.exports = { createSlide };
