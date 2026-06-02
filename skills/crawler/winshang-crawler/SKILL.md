---
name: winshang-crawler
emoji: 🏗️
description: 赢商大数据爬虫 — 爬取商业地产项目数据，支持按城市/状态筛选
requires:
  bins: [python3, uv]
  env:
    - WINSHANG_USERNAME
    - WINSHANG_PASSWORD
---

# 赢商大数据爬虫 (Winshang Crawler)

爬取赢商大数据网站（winshangdata.com）的商业地产项目信息，包括项目名称、状态、商业面积、所在城市等字段。

## 执行流程

当用户查询项目数据时，按以下顺序执行：

1. 直接运行 `query` 命令查看已有数据
2. 如果报错"文件不存在"，先运行 `crawl` 爬取全量数据，再运行 `query`

**不要从其他网站抓取**，所有数据只通过 winshang-crawler 的 CLI 命令获取。

## 使用场景

- "查一下上海有哪些未开业的购物中心"
- "帮我爬取北京的新项目数据"
- "查询已爬取的广州项目"
- "更新之前爬取的数据"

## 触发指令

### 爬取项目数据

```
uv run python -m src.crawler.cli crawl --province 上海 --status 未开业
```

参数说明：
- `--province` / `-p`: 省份或城市名，如 `上海`、`北京`、`广东`（空=全国）
- `--status` / `-s`: 项目状态，`未开业`（默认）、`已开业`、`""`（全部）
- `--output` / `-o`: 输出 CSV 路径（默认 `./data/winshang_data.csv`）

输出文件为 CSV 格式，包含：projectId、项目名称、项目状态、项目类型、商业面积等字段。

### 查询已爬取的数据

```
uv run python -m src.crawler.cli query --province 广东
uv run python -m src.crawler.cli query --city 广州 --status 已开业 --year 2025
uv run python -m src.crawler.cli query --status 未开业 --year-after 2020
```

参数说明：
- `--file` / `-f`: CSV 文件路径（默认 `./data/winshang_data.csv`）
- `--province` / `-p`: 按省份筛选（如 广东、浙江、江苏、福建、山东、四川）
- `--city` / `-c`: 按城市筛选
- `--status` / `-s`: 按项目状态筛选（未开业/已开业）
- `--year` / `-y`: 按开业年份筛选
- `--year-after` / `-ya`: 开业年份在指定年份之后
- `--limit` / `-l`: 显示条数上限（默认 10）

## 安装与配置

1. 克隆项目后，执行 `uv sync && uv run playwright install chromium`
2. 在项目根目录创建 `.env` 文件，填入凭据：

```
WINSHANG_USERNAME=your_email@example.com
WINSHANG_PASSWORD=your_password
```

3. 执行 `uv run python -m src.crawler.cli crawl` 开始爬取

## 输出示例

```
项目名称 | 项目状态 | 所在城市 | 商业面积
北京湾里WANLI | 未开业 | 北京 | 20万平米以上
上海昌港荟 | 未开业 | 上海 | 5万平米以下
```

## 注意事项

- 首次运行会通过 Playwright 登录获取 JWT token（约 10s），后续 API 调用走 httpx 直连
- 数据保存在 `data/winshang_data.csv`
- 请合理使用，避免高频请求对目标网站造成压力
