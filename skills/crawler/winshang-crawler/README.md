# 赢商大数据爬虫 Skill (Winshang Crawler)

自包含的 Python skill，用于爬取赢商大数据网站（winshangdata.com）的商业地产项目信息。

## 特性

- **完全自包含**：所有代码、依赖配置、文档都在本 skill 目录内
- **uv 管理依赖**：`pyproject.toml` + `uv sync` 即可安装
- **支持两种数据获取模式**：
  - **API 模式**（默认）：通过 httpx 直接调用 JSON API
  - **Playwright 模式**：使用浏览器登录获取 JWT token

## 快速开始

### 1. 安装依赖

```bash
cd skills/crawler/winshang-crawler
uv sync
uv run playwright install chromium
```

### 2. 配置凭据

```bash
cp .env.example .env
# 编辑 .env，填入你的 WINSHANG_USERNAME 和 WINSHANG_PASSWORD
```

### 3. 爬取数据

```bash
# 爬取上海未开业项目
uv run python -m src.crawler.cli crawl --province 上海

# 爬取全国已开业项目
uv run python -m src.crawler.cli crawl --status 已开业

# 输出到自定义路径
uv run python -m src.crawler.cli crawl --province 广东 --output ./data/gd.csv
```

### 4. 查询已爬取的数据

```bash
# 查询广东项目
uv run python -m src.crawler.cli query --province 广东

# 复杂筛选
uv run python -m src.crawler.cli query --city 广州 --status 已开业 --year 2025 --limit 20

# 开业年份在 2020 年之后
uv run python -m src.crawler.cli query --status 未开业 --year-after 2020
```

## 项目结构

```
winshang-crawler/
├── SKILL.md                # Skill 描述（OpenCode 用）
├── README.md               # 本文件
├── pyproject.toml          # uv 项目配置
├── .env.example            # 凭据模板
├── .gitignore              # 忽略敏感文件和缓存
└── src/
    └── crawler/
        ├── __init__.py
        ├── cli.py          # CLI 入口
        ├── service.py      # 业务逻辑
        └── winshang_client.py  # HTTP API 客户端
```

## 数据字段

输出 CSV 包含以下字段：

- `projectId` — 项目 ID
- `项目名称` — 项目名称
- `项目状态` — 未开业 / 已开业
- `所在城市` — 自动提取的城市
- `项目类型` — 物业类型
- `商业面积` — 商业面积区间
- `开业时间` — 预计开业时间
- `招商需求` — 招商情况
- `更新时间` — 数据更新时间
- `项目概况` — 项目介绍
- `页面地址` — 详情页 URL

## 注意事项

- **首次运行**会通过 Playwright 登录获取 JWT token（约 10s），后续 API 调用走 httpx 直连
- **合理使用**：每页请求间隔 1-2s，避免高频请求触发限流
- **数据保存**：CSV 默认保存到 `./data/winshang_data.csv`
- **凭据安全**：`.env` 文件已在 `.gitignore` 中，**不要**提交到 git

## 故障排查

- **登录失败**：检查 `.env` 中的用户名/密码是否正确
- **API 限流**：脚本会自动重试（最长 120s 等待），可观察日志
- **Playwright 错误**：运行 `uv run playwright install chromium` 重新安装浏览器

## 许可证

仅供学习和合法商业用途使用。请遵守目标网站的 robots.txt 和服务条款。
