# kirin-jplatpat

J-PlatPat（日本特許庁プラットフォーム）爬虫工具，提供命令行和 REST API 两种使用方式。

## 功能特性

- 🔍 搜索日本专利数据库 (J-PlatPat)
- 📝 自动提取专利摘要（要約）
- 🌐 提供 FastAPI REST API 接口
- 💻 支持命令行直接调用
- 📊 输出 JSON 格式结果

## 快速开始

### API 方式（推荐）

```bash
# 启动 API 服务
python api.py

# 在另一个终端测试
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "人工知能", "limit": 5}'

# 查看 API 文档
访问 http://localhost:8000/docs
```

### 命令行方式

```bash
# 基本搜索（默认开启摘要提取）
python jplatpat_scraper.py "人工知能"

# 禁用摘要提取（更快）
python jplatpat_scraper.py "人工知能" --no-abstract --limit 5
```

## 项目结构

```
kirin-jplatpat/
├── api.py                      # FastAPI 应用
├── jplatpat_scraper.py         # 命令行爬虫（同步 API）
├── jplatpat_scraper_async.py   # 异步爬虫（API 内部使用）
├── requirements.txt            # Python 依赖
├── Dockerfile                  # 生产镜像
├── .dockerignore               # Docker 排除
├── .env.example                # 环境变量示例
├── README.md                   # 本文件
└── TROUBLESHOOTING.md          # 故障排查指南
```

## 详细使用方法

### 1. REST API 方式

#### 启动 API 服务

```bash
python api.py
```

服务将在 `http://localhost:8000` 启动

#### API 文档

访问 `http://localhost:8000/docs` 查看交互式 API 文档（Swagger UI）

#### API 端点

**POST /search** - 搜索专利

请求示例：
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工知能",
    "limit": 10,
    "timeout": 20000,
    "fetch_abstract": true,
    "headless": true
  }'
```

请求参数：
    "fetch_abstract": true,
    "headless": true
  }'
```

请求参数：
- `query` (必填): 搜索关键词
- `limit` (可选): 返回结果数量，范围 1-100，默认 10
- `timeout` (可选): 超时时间（毫秒），范围 5000-60000，默认 20000
- `fetch_abstract` (可选): 是否提取摘要，默认 true
- `headless` (可选): 是否无头模式运行浏览器，默认 true

### 2. 命令行方式

```bash
# 基本搜索（默认开启摘要提取）
python jplatpat_scraper.py "人工知能"

# 指定返回数量
python jplatpat_scraper.py "人工知能" --limit 20

# 禁用摘要提取（更快）
python jplatpat_scraper.py "人工知能" --no-abstract

# 指定输出文件
python jplatpat_scraper.py "人工知能" -o result.json

# 有头模式运行（调试用）
python jplatpat_scraper.py "人工知能" --headful

# 查看所有选项
python jplatpat_scraper.py --help
```

### 命令行参数

- `query`: 搜索关键词（必填）
- `--limit`: 最大返回结果数，默认 10
- `--timeout`: 超时时间（毫秒），默认 20000
- `--output`, `-o`: 输出文件路径，不指定则自动生成
- `--no-abstract`: 禁用摘要提取（默认启用）
- `--headful`: 有头模式运行浏览器（调试用）

## 输出格式

```json
{
  "query": "人工知能",
  "message": "検索結果: 1-10 / 1234件",
  "count": 10,
  "rows": [
    {
      "no": "1",
      "document_number": "特開2023-123456",
      "document_url": "https://www.j-platpat.inpit.go.jp/...",
      "abstract": "本発明は人工知能に関する...",
      "application_number": "2022-012345",
      "application_date": "2022.01.15",
      "publication_date": "2023.08.20",
      "invention_title": "人工知能システム",
      "applicant": "株式会社ABC",
      "status": "公開",
      "fi_codes": ["G06N3/00"],
      "actions": ["詳細", "経過情報"]
    }
  ]
}
```

## 配置

可以通过 `.env` 文件配置默认参数（参考 `.env.example`）

## Docker 部署

### 使用 Docker 命令（推荐）

```bash
# 构建镜像
docker build -t jplatpat-api .

# 运行容器
docker run -d \
  --name jplatpat-api \
  -p 8000:8000 \
  jplatpat-api

# 查看日志
docker logs -f jplatpat-api

# 停止容器
docker stop jplatpat-api
```

### 健康检查

```bash
# 检查容器健康状态
docker ps

# 访问健康检查端点
curl http://localhost:8000/health
```

## 生产部署

### 使用 Gunicorn + Uvicorn workers（非 Docker）

```bash
pip install gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 资源配置

根据实际需求为容器设置 CPU/内存等资源限制

## 注意事项

- 摘要提取会显著增加执行时间，因为需要逐个打开专利详情页
- 建议在生产环境使用 headless 模式
- 大量请求时注意遵守 J-PlatPat 的使用条款
- API 服务默认开启 CORS，生产环境请根据需要配置

## License

MIT
