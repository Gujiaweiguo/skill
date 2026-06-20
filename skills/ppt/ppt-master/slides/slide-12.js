function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('商圈会员CRM系统', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addShape(pres.ShapeType.rect, {
    x: 0.8, y: 1.4, w: 8.4, h: 3.6, fill: { color: 'f8f9fa' }, rectRadius: 0.1
  });
  slide.addText('集团级会员管理', {
    x: 1.2, y: 1.6, w: 2.5, h: 0.35,
    fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
  });
  slide.addText(' — 多项目、多业态统一会员账户', {
    x: 3.7, y: 1.6, w: 4.5, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
  });
  slide.addText('积分营销体系', {
    x: 1.2, y: 2.15, w: 2.5, h: 0.35,
    fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
  });
  slide.addText(' — AI智能积分、小票AI自助积分', {
    x: 3.7, y: 2.15, w: 4.5, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
  });
  slide.addText('私域商城', {
    x: 1.2, y: 2.7, w: 2.5, h: 0.35,
    fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
  });
  slide.addText(' — 会员小程序+积分商城', {
    x: 3.7, y: 2.7, w: 4.5, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
  });
  slide.addText('企微SCRM', {
    x: 1.2, y: 3.25, w: 2.5, h: 0.35,
    fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
  });
  slide.addText(' — 社群运营、企微标签、任务下发', {
    x: 3.7, y: 3.25, w: 4.5, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
  });
  slide.addText('第三方对接', {
    x: 1.2, y: 3.8, w: 2.5, h: 0.35,
    fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
  });
  slide.addText(' — 停车系统、POS收银、充电桩等', {
    x: 3.7, y: 3.8, w: 4.5, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
  });
  slide.addText('12', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
