function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('AI Skills 技术底座', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  const techs = [
    { icon: '🔮', title: 'RAG 知识库', desc: '私域数据向量化，支持精准问答' },
    { icon: '🗄️', title: 'Text-to-SQL', desc: '自然语言→数据查询，无需IT介入' },
    { icon: '🤖', title: 'Agent 工作流', desc: '多步骤任务编排，自动执行' },
    { icon: '🔗', title: '模型无关架构', desc: '兼容主流大模型（DeepSeek/通义千问/文心等）' },
    { icon: '🔒', title: '私有化部署', desc: '满足国企数据安全合规要求' }
  ];
  techs.forEach((t, i) => {
    const y = 1.5 + i * 0.7;
    slide.addShape(pres.ShapeType.rect, {
      x: 0.8, y: y, w: 8.4, h: 0.6, fill: { color: i % 2 === 0 ? 'f8f9fa' : 'ffffff' }, rectRadius: 0.05
    });
    slide.addText(t.icon, { x: 1, y: y + 0.05, w: 0.5, h: 0.5, fontSize: 20 });
    slide.addText(t.title, {
      x: 1.6, y: y, w: 2.5, h: 0.6,
      fontSize: 15, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
    });
    slide.addText(t.desc, {
      x: 4.2, y: y, w: 5, h: 0.6,
      fontSize: 13, fontFace: 'Microsoft YaHei', color: theme.secondary, valign: 'middle'
    });
  });
  slide.addText('09', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
