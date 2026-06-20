function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('客户案例：广州城投商业 — 大会员+联合运营', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 24, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addShape(pres.ShapeType.rect, {
    x: 0.8, y: 1.4, w: 4.2, h: 3.4, fill: { color: 'f0f7ff' }, rectRadius: 0.1
  });
  slide.addText('项目概况', {
    x: 1, y: 1.5, w: 3.8, h: 0.4,
    fontSize: 14, fontFace: 'Microsoft YaHei', color: theme.accent, bold: true
  });
  slide.addText('广州市城投集团旗下商业板块', {
    x: 1, y: 2, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('管理超300万㎡商业物业', {
    x: 1, y: 2.25, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('含写字楼、商场、产业园等多业态', {
    x: 1, y: 2.5, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addShape(pres.ShapeType.rect, { x: 1, y: 3, w: 1.5, h: 0.03, fill: { color: theme.light } });
  slide.addText('客户痛点：业态多元、会员数据分散、运营团队编制有限', {
    x: 1, y: 3.4, w: 3.8, h: 0.3,
    fontSize: 10, fontFace: 'Microsoft YaHei', color: '888888', italic: true
  });
  slide.addShape(pres.ShapeType.rect, {
    x: 5.2, y: 1.4, w: 4.2, h: 3.4, fill: { color: 'ffffff' }, rectRadius: 0.1,
    shadow: { type: 'outer', blur: 5, offset: 2, color: '000000', opacity: 0.07 }
  });
  slide.addText('蓝联方案', {
    x: 5.4, y: 1.5, w: 3.8, h: 0.4,
    fontSize: 14, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  var items = ['集团大会员体系搭建', '多项目会员数据统一', '私域小程序商城', '联合运营团队派驻', '年度营销活动策划', '数据运营报告输出'];
  items.forEach(function(item, i) {
    var y = 2.1 + i * 0.4;
    slide.addText('▸ ' + item, {
      x: 5.4, y: y, w: 3.8, h: 0.35,
      fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
    });
  });
  slide.addText('14', { x: 9, y: 5.1, w: 0.8, h: 0.25, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
