function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('AI智能问数系统 — ChatBI', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  var features = [
    { icon: '🗣️', title: '自然语言查询', lines: ['说人话就能查数据', '"上个月会员消费TOP10是谁？"'] },
    { icon: '🔌', title: '多源数据接入', lines: ['聚合CRM、ERP、POS', '停车等多系统数据'] },
    { icon: '📊', title: '智能可视化', lines: ['自动生成图表', '数据趋势一目了然'] },
    { icon: '📱', title: '领导驾驶舱', lines: ['移动端+PC端', '随时随地掌握经营状况'] }
  ];
  features.forEach(function(f, i) {
    var col = i % 2, row = Math.floor(i / 2);
    var x = 0.8 + col * 4.5;
    var y = 1.5 + row * 1.8;
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: y, w: 4.1, h: 1.7, fill: { color: 'ffffff' }, rectRadius: 0.1,
      shadow: { type: 'outer', blur: 5, offset: 2, color: '000000', opacity: 0.07 }
    });
    slide.addText(f.icon, { x: x + 0.2, y: y + 0.2, w: 0.6, h: 0.6, fontSize: 28 });
    slide.addText(f.title, {
      x: x + 0.8, y: y + 0.2, w: 3, h: 0.5,
      fontSize: 16, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
    });
    f.lines.forEach(function(line, li) {
      slide.addText(line, {
        x: x + 0.3, y: y + 0.8 + li * 0.35, w: 3.5, h: 0.3,
        fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary
      });
    });
  });
  slide.addText('10', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
