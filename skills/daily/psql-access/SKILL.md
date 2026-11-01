---
name: psql-access
description: "WSL2 主机 PostgreSQL 访问约定（主机级环境事实，非项目代码）。当需要连接/查询数据库、使用 psql / postgres / pgvector、查库、连库、排查 RAG 向量数据，或遇到 psql: command not found、密码认证失败、pg_dump 版本不匹配时使用。覆盖共享实例 postgres-shared 的两条连接路径（docker exec 与 host psql）、免硬编码密码的 PGPASSWORD 取法与常用查询配方。"
compatibility: Pure prompt skill. 无运行时依赖。描述的是主机级共享 PostgreSQL 实例；项目自有数据库（.env / docker-compose 定义的）以项目配置为准，本 skill 不覆盖。
---

# psql-access / 主机 PostgreSQL 访问约定

## 环境事实（2026-11-01 实测）

- 主机：WSL2 Ubuntu 22.04；已装 `postgresql-client-16`（16.15，阿里云 PGDG `jammy-pgdg` 源，见 `/etc/apt/sources.list.d/pgdg.list`），`psql`/`pg_dump` 直接可用
- 共享实例：Docker 容器 `postgres-shared`（镜像 `pgvector/pgvector:pg16`），映射 `localhost:5432`，超级用户 `postgres`
- 容器内自带 psql 16.14；主机 16.15 与服务端 16 同代，无版本警告
- 密码在容器环境变量 `POSTGRES_PASSWORD` 中，**不要硬编码到命令、脚本或文档**

## 连接手法（按优先级）

1. **docker exec**（零依赖，永远可用，且只到得了这一个容器）：

   ```bash
   docker exec -it postgres-shared psql -U postgres [-d <db>]        # 交互
   docker exec postgres-shared psql -U postgres -d <db> -c '<sql>'   # 单条
   docker exec -i postgres-shared psql -U postgres -d <db> < file.sql  # 执行文件
   ```

2. **host psql**（若已安装 `postgresql-client`；密码现取，不落历史）：

   ```bash
   PGPASSWORD=$(docker exec postgres-shared printenv POSTGRES_PASSWORD) \
     psql -h localhost -p 5432 -U postgres -d <db>
   ```

3. **一次性配置 ~/.pgpass**（`chmod 600`，格式 `localhost:5432:*:postgres:<密码>`）后 host psql 免密。

## 版本坑

- Ubuntu 22.04 默认 apt 源只有 **psql 14**：连 pg16 服务端日常查询可用（仅无害警告），但 **pg_dump 14 拒绝 pg16**——本机已装 16 不受影响；其他机器若只有 14，dump 走容器内的 16：

   ```bash
   docker exec postgres-shared pg_dump -U postgres <db> > dump.sql
   ```

## 常用配方

```sql
\l                          -- 列库
\dt                         -- 列表
\d <table>                  -- 表结构
select count(*) from <t>;   -- 计数
select * from pg_extension where extname='vector';  -- pgvector 装没装
```

- 导出 CSV：`psql ... -c "\copy (select ...) to '/tmp/x.csv' csv header"`
- 连任意远端库（其他容器/测试库/Windows 侧）只能走 host psql：`-h <host>`

## 项目自有库优先

项目 `.env` / `docker-compose` 定义了自己的数据库时，**以项目配置为准**；本 skill 只覆盖主机共享实例与通用手法。

## 故障对照

| 症状 | 处理 |
|---|---|
| `psql: command not found` | 走 docker exec，或 `sudo apt install postgresql-client` |
| `password authentication failed` | 用上面 PGPASSWORD 取法，勿猜密码 |
| `pg_dump: server version mismatch` | 必须用容器内 16 版 pg_dump |
| 连不上 localhost:5432 | `docker ps` 确认 postgres-shared 在跑 |
