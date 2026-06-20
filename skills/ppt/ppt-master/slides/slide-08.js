function createSlide(pres, theme) {
  var slide = pres.addSlide();
  slide.background = { color: theme.bg };
  slide.addText('AI Skills — 商业地产全场景AI工作流', {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.8, y: 1.1, w: 1.5, h: 0.04, fill: { color: theme.accent } });
  slide.addText('面向商业地产各业务岗位的AI增强工具集', {
    x: 0.8, y: 1.3, w: 8.4, h: 0.35,
    fontSize: 12, fontFace: 'Microsoft YaHei', color: '888888'
  });
  var skills = [
    { icon: '📊', title: 'AI问数', lines: ['自然语言查询经营数据', '支持会员/客流/租金/招商多维分析'] },
    { icon: '💬', title: 'AI客服', lines: ['智能问答+工单联动', '覆盖商场导购、物业报修、招商咨询'] },
    { icon: '🔍', title: '招商研究', lines: ['基于RAG的品牌知识库', '辅助招商分析与品牌匹配'] },
    { icon: '📋', title: '工程工单', lines: ['工单智能派发、进度追踪', '巡检报告自动生成'] },
    { icon: '📝', title: '运营助手', lines: ['活动策划、内容生成', '报表自动输出'] },
    { icon: '📈', title: '数据分析', lines: ['多源数据整合', 'AI自动洞察与预警'] }
  ];
  skills.forEach(function(s, i) {
    var col = i % 3, row = Math.floor(i / 3);
    var x = 0.8 + col * 3.05;
    var y = 1.8 + row * 1.7;
    slide.addShape(pres.ShapeType.rect, {
      x: x, y: y, w: 2.75, h: 1.6, fill: { color: 'ffffff' }, rectRadius: 0.08,
      shadow: { type: 'outer', blur: 4, offset: 1, color: '000000', opacity: 0.06 },
      line: { color: theme.light, width: 0.8 }
    });
    slide.addText(s.icon, {
      x: x + 0.15, y: y + 0.15, w: 0.5, h: 0.5, fontSize: 24
    });
    slide.addText(s.title, {
      x: x + 0.65, y: y + 0.15, w: 1.9, h: 0.4,
      fontSize: 14, fontFace: 'Microsoft YaHei', color: theme.primary, bold: true, valign: 'middle'
    });
    s.lines.forEach(function(line, li) {
      slide.addText(line, {
        x: x + 0.15, y: y + 0.65 + li * 0.35, w: 2.45, h: 0.3,
        fontSize: 11, fontFace: 'Microsoft YaHei', color: theme.secondary
      });
    });
  });
  slide.addText('08', { x: 9, y: 5.15, w: 0.8, h: 0.3, fontSize: 10, fontFace: 'Microsoft YaHei', color: '999999', align: 'right' });
}
module.exports = { createSlide };
