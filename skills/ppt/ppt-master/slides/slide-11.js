function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('AI知识库与工作流平台', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addText('基于RAG与Agent技术，构建企业级智能知识中枢', {
    x: 0.8, y: 1.3, w: 8.4, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: '888888'
  });
  const items = [
    { icon: '📚', title: '企业内部知识库', body: '规章制度、招商手册、服务SOP等统一管理' },
    { icon: '🤖', title: '智能问答助手', body: '员工或租户提问，AI即时作答' },
    { icon: '📄', title: '文档智能处理', body: 'PDF/Word/Excel自动解析入库' },
    { icon: '⚙️', title: '工作流引擎', body: '工单流转、审批流程、自动提醒' }
  ];
  items.forEach((item, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.8 + col * 4.5;
    const y = 1.8 + row * 1.6;
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: y, w: 4.1, h: 1.5, fill: { color: 'ffffff' }, rectRadius: 0.1,
      shadow: { type: 'outer', blur: 5, offset: 2, color: '000000', opacity: 0.07 }
    });
    slide.addText(item.icon, { x: x + 0.2, y: y + 0.15, w: 0.6, h: 0.5, fontSize: 26 });
    slide.addText(item.title, {
      x: x + 0.8, y: y + 0.15, w: 3, h: 0.45,
      fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
    });
    slide.addText(item.body, {
      x: x + 0.3, y: y + 0.7, w: 3.5, h: 0.6,
      fontSize: 12, fontFace: 'Microsoft YaHei', color: theme.secondary, lineSpacing: 1.3
    });
  });
  slide.addText('11', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
