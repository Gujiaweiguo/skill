function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('客户案例：广州白云国资 — 联合运营标杆', {
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
  slide.addText('广州白云国有资产经营有限公司', {
    x: 1, y: 2, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('白云区属国企', {
    x: 1, y: 2.25, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('管理多个社区商业项目', {
    x: 1, y: 2.5, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addText('国企数字化转型试点', {
    x: 1, y: 2.75, w: 3.8, h: 0.25,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
  });
  slide.addShape(pres.ShapeType.rect, { x: 1, y: 3.1, w: 1.5, h: 0.03, fill: { color: theme.light } });
  slide.addText('核心诉求：数字化运营从0到1，团队无运营经验', {
    x: 1, y: 3.4, w: 3.8, h: 0.3,
    fontSize: 10, fontFace: 'Microsoft YaHei', color: '888888', italic: true
  });
  slide.addShape(pres.ShapeType.rect, {
    x: 5.2, y: 1.4, w: 4.2, h: 3.4, fill: { color: 'e8f5e9' }, rectRadius: 0.1
  });
  slide.addText('联合运营成果', {
    x: 5.4, y: 1.5, w: 3.8, h: 0.4,
    fontSize: 14, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  var items = ['CRM+小程序上线', '会员拉新20000+', '年度营销活动15场', '新媒体矩阵搭建', '联合运营团队日活', '移交运营SOP手册'];
  items.forEach(function(item, i) {
    var y = 2.1 + i * 0.4;
    slide.addText('✓ ' + item, {
      x: 5.4, y: y, w: 3.8, h: 0.35,
      fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
    });
  });
  slide.addText('16', { x: 9, y: 5.1, w: 0.8, h: 0.25, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
