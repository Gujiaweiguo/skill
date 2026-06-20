function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.primary };
  slide.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText('感谢聆听', {
    x: 1, y: 1.5, w: 8, h: 1.5,
    fontSize: 48, fontFace: 'Microsoft YaHei', color: 'ffffff', bold: true, align: 'center'
  });
  slide.addShape(pres.ShapeType.rect, { x: 3.5, y: 3.3, w: 3, h: 0.04, fill: { color: theme.accent } });
  slide.addText('期待与广州海港地产携手共进', {
    x: 1, y: 3.5, w: 8, h: 0.6,
    fontSize: 20, fontFace: 'Microsoft YaHei', color: theme.light, align: 'center'
  });
  slide.addText('蓝联科技有限公司', {
    x: 1, y: 4.3, w: 8, h: 0.4,
    fontSize: 14, fontFace: 'Microsoft YaHei', color: '999999', align: 'center'
  });
  slide.addText('www.lanlnk.com | 400-xxx-xxxx', {
    x: 1, y: 4.7, w: 8, h: 0.4,
    fontSize: 14, fontFace: 'Microsoft YaHei', color: '999999', align: 'center'
  });
  slide.addShape(pres.ShapeType.rect, { x: 0, y: 5.565, w: 10, h: 0.06, fill: { color: theme.accent } });
}
module.exports = { createSlide };
