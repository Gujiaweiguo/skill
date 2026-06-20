function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('合作展望', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  var phases = [
    { phase: '第一阶段', title: '联合运营启动', color: theme.accent,
      items: ['运营调研与方案确认', '团队组建与入驻', 'CRM/商城快速部署', '首期营销活动策划执行', '数据看板上线', '月度运营报告'],
      note: '1-2个月' },
    { phase: '第二阶段', title: 'AI能力导入', color: theme.primary,
      items: ['AI智能问数系统部署', 'AI知识库搭建', 'AI客服机器人上线', '工作流自动化', '运营策略AI优化'],
      note: '3-6个月' },
    { phase: '第三阶段', title: '全面深化', color: theme.light,
      items: ['AI+运营深度融合', '数据驱动决策体系', '多项目复制推广', '知识转移完成', '国企自有团队独立运营'],
      note: '6-12个月' }
  ];
  phases.forEach(function(p, i) {
    var x = 0.8 + i * 3.05;
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: 1.5, w: 2.75, h: 3.0, fill: { color: 'ffffff' }, rectRadius: 0.08,
      shadow: { type: 'outer', blur: 5, offset: 2, color: '000000', opacity: 0.07 },
      line: { color: p.color, width: 1.5 }
    });
    slide.addShape(pres.ShapeType.rect, { x: x, y: 1.5, w: 2.75, h: 0.5, fill: { color: p.color }, rectRadius: 0.08 });
    slide.addText(p.phase, {
      x: x, y: 1.5, w: 2.75, h: 0.25,
      fontSize: 11, fontFace: 'Microsoft YaHei', color: 'ffffff', align: 'center', valign: 'middle'
    });
    slide.addText(p.title, {
      x: x, y: 1.8, w: 2.75, h: 0.2,
      fontSize: 11, fontFace: 'Microsoft YaHei', color: 'ffffff', align: 'center', valign: 'top'
    });
    p.items.forEach(function(item, j) {
      var iy = 2.2 + j * 0.35;
      slide.addText('▸ ' + item, {
        x: x + 0.15, y: iy, w: 2.45, h: 0.3,
        fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
      });
    });
  });
  slide.addShape(pres.ShapeType.rect, {
    x: 0.8, y: 4.7, w: 8.4, h: 0.03, fill: { color: theme.accent }
  });
  slide.addText('以联合运营为起点，以AI赋能为主线，逐步构建国企数字化运营体系', {
    x: 0.8, y: 4.8, w: 8.4, h: 0.3,
    fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary, align: 'center', italic: true
  });
  slide.addText('19', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
