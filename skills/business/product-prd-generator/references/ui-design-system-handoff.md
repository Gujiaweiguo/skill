# UI / Design System Handoff

统一前端 UI 是产品变更的一类可追踪语义，不应只写成“页面风格统一”。

## UI Model

UI 相关增量 PRD 可以引用：

```yaml
ui_model:
  design_system_id: lnk-design-v1
  page_pattern: list-page-v2
  affected_routes: [/contracts]
  shared_components: [PageHeader, FilterBar, DataTable, EmptyState]
  visual_evidence:
    state: observed | not_found | stale | inaccessible
    viewport: desktop-1440x900
    refs: []
```

UI Model 至少分四层：design tokens、shared components、page patterns、individual page migrations。

## 验收

UI 需求必须同时声明：

- 功能验收：路由、表单、权限、加载、空态、错误态；
- 视觉验收：viewport、截图/diff、基线版本；
- 可访问性或交互验收：键盘、焦点、语义标签（适用时）；
- 基线不可用时的状态，不得声称视觉一致。

全站 UI 改造应拆成 design-system foundation、common components、page patterns 和页面迁移，不得生成一个无边界的单一 change。
