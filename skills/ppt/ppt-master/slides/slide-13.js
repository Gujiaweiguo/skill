function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('联合运营模式 — 国企轻量化运营的最佳选择', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 24, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addShape(pres.ShapeType.rect, {
    x: 0.8, y: 1.4, w: 4.2, h: 3.5, fill: { color: 'f0f7ff' }, rectRadius: 0.1
  });
  slide.addText('什么是联合运营？', {
    x: 1, y: 1.5, w: 3.8, h: 0.45,
    fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.accent, bold: true
  });
  slide.addText('蓝联派驻专业运营团队，', {
    x: 1, y: 2, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('与客户共建运营体系，按结果付费。', {
    x: 1, y: 2.25, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('客户无需增加编制，', {
    x: 1, y: 2.5, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('即可拥有完整的数字化运营能力。', {
    x: 1, y: 2.75, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('服务内容', {
    x: 1, y: 3.1, w: 3.8, h: 0.35,
    fontSize: 13, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addText('▸ 私域运营 — 会员拉新、社群运营、精准营销', {
    x: 1, y: 3.5, w: 3.8, h: 0.25,
    fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('▸ 营销企划 — 年度营销日历、主题活动策划执行', {
    x: 1, y: 3.75, w: 3.8, h: 0.25,
    fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('▸ 新媒体运营 — 公众号/视频号/小红书内容运营', {
    x: 1, y: 4.0, w: 3.8, h: 0.25,
    fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('▸ 数据运营 — 经营分析报表、运营策略优化', {
    x: 1, y: 4.25, w: 3.8, h: 0.25,
    fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addShape(pres.ShapeType.rect, {
    x: 5.2, y: 1.4, w: 4.2, h: 3.5, fill: { color: 'e8f5e9' }, rectRadius: 0.1
  });
  slide.addText('为什么国企适合联合运营？', {
    x: 5.4, y: 1.5, w: 3.8, h: 0.45,
    fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  var reasons = [
    { title: '不增编制', desc: '专业团队派驻，无需扩编' },
    { title: '风险可控', desc: '分阶段交付，按效果付费' },
    { title: '知识转移', desc: '运营方法论逐步内化给国企自有团队' },
    { title: '快速启动', desc: '已有成熟运营SOP，直接导入' }
  ];
  reasons.forEach(function(r, i) {
    var y = 2.1 + i * 0.6;
    slide.addShape(pres.ShapeType.rect, {
      x: 5.4, y: y, w: 0.35, h: 0.35, fill: { color: theme.accent }, rectRadius: 0.03
    });
    slide.addText('✓', { x: 5.4, y: y - 0.02, w: 0.35, h: 0.35, fontSize: 14, color: 'ffffff', align: 'center', valign: 'middle' });
    slide.addText(r.title, {
      x: 5.9, y: y, w: 1.5, h: 0.35,
      fontSize: 13, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
    });
    slide.addText(r.desc, {
      x: 7.4, y: y, w: 2, h: 0.35,
      fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
    });
  });
  slide.addShape(pres.ShapeType.rect, { x: 5.4, y: 4.7, w: 3.8, h: 0.03, fill: { color: theme.light } });
  slide.addText('已落地：天河新天地、广州金沙汇、白云国资等', {
    x: 5.4, y: 4.8, w: 3.8, h: 0.3,
    fontSize: 10, fontFace: 'Microsoft YaHei', color: '888888', italic: true
  });
  slide.addText('13', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
