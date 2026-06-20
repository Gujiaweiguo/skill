function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('广州本地案例集', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addText('扎根广州，服务本地商业地产', {
    x: 0.8, y: 1.3, w: 8.4, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: '888888'
  });
  var cases = [
    { name: '广州流花中心', desc: '流花商圈核心 | 会员+积分商城 | 2024上线' },
    { name: '广州国际时尚中心', desc: '白云区 | 商业服务平台 | 2024上线' },
    { name: '广州金沙汇', desc: '金沙洲 | CRM+联合运营 | 2023上线' },
    { name: '萝岗和苑', desc: '黄埔区 | 社区商业会员系统 | 2024上线' }
  ];
  cases.forEach(function(c, i) {
    var x = 0.8;
    var y = 1.8 + i * 0.78;
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: y, w: 8.4, h: 0.68, fill: { color: 'ffffff' }, rectRadius: 0.06,
      shadow: { type: 'outer', blur: 3, offset: 1, color: '000000', opacity: 0.05 }
    });
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: y, w: 0.06, h: 0.68, fill: { color: theme.accent }
    });
    slide.addText(c.name, {
      x: x + 0.3, y: y + 0.05, w: 3.2, h: 0.35,
      fontSize: 14, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
    });
    slide.addText(c.desc, {
      x: x + 3.6, y: y + 0.05, w: 4.6, h: 0.35,
      fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
    });
  });
  slide.addText('17', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
