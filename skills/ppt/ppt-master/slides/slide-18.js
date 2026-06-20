function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('为什么选择蓝联？', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  var points = [
    { title: '30+', subtitle: '商业地产项目', body: '深耕商业地产行业，覆盖国企、上市企业等客户' },
    { title: '10年+', subtitle: '行业经验', body: '从传统ERP到AI，持续服务商业地产数字化' },
    { title: 'AI+运营', subtitle: '双重能力', body: '产品自研+联合运营，不仅做系统，更重结果' },
    { title: 'SOE经验', subtitle: '国企定制服务', body: '深谙国企决策流程与合规要求，交付无忧' },
    { title: '本地服务', subtitle: '广州总部', body: '总部在广州，响应迅速，服务可触达' }
  ];
  points.forEach(function(p, i) {
    var y = 1.5 + i * 0.68;
    slide.addShape(pres.ShapeType.rect, {
      x: 0.8, y: y, w: 8.4, h: 0.62, fill: { color: i % 2 === 0 ? 'f8f9fa' : 'ffffff' }, rectRadius: 0.05
    });
    slide.addShape(pres.ShapeType.rect, {
      x: 0.8, y: y, w: 0.08, h: 0.62, fill: { color: theme.accent }
    });
    slide.addText(p.title, {
      x: 1.1, y: y, w: 1.2, h: 0.62,
      fontSize: 20, fontFace: 'Microsoft YaHei', color: theme.accent, bold: true, valign: 'middle', align: 'center'
    });
    slide.addText(p.subtitle, {
      x: 2.5, y: y, w: 1.8, h: 0.62,
      fontSize: 14, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
    });
    slide.addText(p.body, {
      x: 4.4, y: y, w: 4.6, h: 0.62,
      fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
    });
  });
  slide.addText('18', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
