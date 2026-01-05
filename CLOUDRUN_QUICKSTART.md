# Cloud Run 部署完整指南

## 📋 目录

1. [快速开始](#快速开始)
2. [准备工作](#准备工作)
3. [部署步骤](#部署步骤)
4. [验证部署](#验证部署)
5. [常见问题](#常见问题)
6. [监控和维护](#监控和维护)

## 🚀 快速开始

### 最快的方式（使用脚本）

```bash
# 1. 获取您的 GCP 项目 ID
export PROJECT_ID=your-project-id

# 2. 运行检查脚本
bash check-cloudrun.sh

# 3. 运行部署脚本
bash deploy-cloudrun.sh $PROJECT_ID
```

部署完成后，您将获得一个类似这样的 URL：
```
https://jplatpat-api-xxxx-asia-northeast1.a.run.app
```

## 📦 准备工作

### 1. 前置条件

- ✅ 有效的 Google Cloud 账户
- ✅ 创建了 GCP 项目
- ✅ 已启用计费
- ✅ 本地安装了 `gcloud` CLI
- ✅ 本地安装了 `docker`

### 2. 安装必要工具

```bash
# macOS
brew install --cask google-cloud-sdk

# Ubuntu/Debian
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 登录 Google Cloud
gcloud init
gcloud auth login
```

### 3. 启用必要的 API

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com
```

## 🔧 部署步骤

### Step 1: 准备部署环境

```bash
# 进入项目目录
cd /workspaces/kirin-jplatpat

# 设置项目 ID
export PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"

# 赋予脚本执行权限
chmod +x deploy-cloudrun.sh check-cloudrun.sh
```

### Step 2: 运行部署前检查

```bash
bash check-cloudrun.sh
```

这个脚本会验证：
- ✅ gcloud CLI 已安装
- ✅ Docker 已安装
- ✅ 已登录 Google Cloud
- ✅ GCP 项目已设置
- ✅ 必要文件存在
- ✅ 所需 API 已启用

### Step 3: 执行部署

```bash
bash deploy-cloudrun.sh $PROJECT_ID
```

或指定区域：

```bash
# 东京（推荐日本用户）
bash deploy-cloudrun.sh $PROJECT_ID asia-northeast1

# 美国
bash deploy-cloudrun.sh $PROJECT_ID us-central1

# 欧洲
bash deploy-cloudrun.sh $PROJECT_ID europe-west1
```

部署脚本会：
1. 创建 Artifact Registry 仓库
2. 构建 Docker 镜像
3. 推送到 Artifact Registry
4. 在 Cloud Run 上部署服务
5. 配置自动扩展和资源限制

### Step 4: 获取服务 URL

```bash
SERVICE_URL=$(gcloud run services describe jplatpat-api \
  --region=asia-northeast1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"
```

## ✅ 验证部署

### 1. 访问 API 文档

```bash
# 在浏览器中打开
open "$SERVICE_URL/docs"

# 或使用 curl
curl -s "$SERVICE_URL/docs" | head -20
```

### 2. 测试健康检查端点

```bash
curl "$SERVICE_URL/health"
# 预期返回: {"status":"ok"}
```

### 3. 测试搜索功能

```bash
curl -X POST "$SERVICE_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工知能",
    "limit": 5,
    "timeout": 20000,
    "fetch_abstract": true,
    "headless": true
  }'
```

### 4. 查看服务状态

```bash
# 获取服务详情
gcloud run services describe jplatpat-api \
  --region=asia-northeast1

# 查看最近的日志
gcloud run logs read jplatpat-api \
  --region=asia-northeast1 \
  --limit=50
  --follow

# 实时查看日志
gcloud run logs read jplatpat-api \
  --region=asia-northeast1 \
  --follow
```

## 🔄 自动部署（CI/CD）

### 使用 GitHub Actions

部署脚本已经创建了 `.github/workflows/deploy-cloudrun.yml` 文件。

#### 配置步骤：

1. **设置 GitHub Secrets**

   按照 [GITHUB_SECRETS_SETUP.md](./GITHUB_SECRETS_SETUP.md) 的说明配置：
   - `GCP_PROJECT_ID`
   - `WIF_PROVIDER`（或 `GCP_SA_KEY`）
   - `WIF_SERVICE_ACCOUNT`

2. **推送代码**

   ```bash
   git add .github/workflows/deploy-cloudrun.yml
   git commit -m "Add Cloud Run CI/CD workflow"
   git push origin main
   ```

3. **自动部署触发**

   之后每次推送到 `main` 分支时，GitHub Actions 会自动：
   - 构建 Docker 镜像
   - 推送到 Artifact Registry
   - 部署到 Cloud Run

## 📊 监控和维护

### 1. 查看运行指标

```bash
# 获取最后 1 小时的请求数
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --format=table

# 获取错误率
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"' \
  --format=table
```

### 2. 设置告警

在 Google Cloud Console 中：
1. 转到 **Monitoring > Alerting**
2. 创建告警策略
3. 选择指标（如错误率、延迟等）
4. 设置通知渠道

### 3. 查看成本

```bash
# 显示当月的估计成本
gcloud billing budgets list
```

### 4. 更新部署

```bash
# 修改代码后，重新部署最新版本
bash deploy-cloudrun.sh $PROJECT_ID

# 或手动触发部署
gcloud run deploy jplatpat-api \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/jplatpat-api/jplatpat-api:latest \
  --region=asia-northeast1
```

### 5. 查看历史修订版本

```bash
# 列出所有修订版本
gcloud run revisions list jplatpat-api \
  --region=asia-northeast1

# 回滚到之前的版本
gcloud run deploy jplatpat-api \
  --revision=jplatpat-api-00001-xxxx \
  --region=asia-northeast1
```

## 🎯 配置说明

### 资源配置

| 配置 | 推荐值 | 说明 |
|------|-------|-----|
| Memory | 2Gi | Playwright 浏览器需要足够内存 |
| CPU | 2 | 处理并发请求 |
| Timeout | 600s | 长期爬取操作 |
| Max Instances | 10 | 自动扩展上限 |
| Min Instances | 0 | 闲置时关闭实例 |
| Concurrency | 50 | 每个实例的最大并发请求 |

### 调整配置

```bash
# 增加内存和 CPU
gcloud run deploy jplatpat-api \
  --memory=4Gi \
  --cpu=4 \
  --region=asia-northeast1

# 调整自动扩展
gcloud run deploy jplatpat-api \
  --min-instances=1 \
  --max-instances=20 \
  --region=asia-northeast1

# 调整超时时间
gcloud run deploy jplatpat-api \
  --timeout=900 \
  --region=asia-northeast1
```

## 💰 成本优化

### 1. 使用最小实例

```bash
# 设置最小实例为 0（默认），在无流量时自动关闭
gcloud run deploy jplatpat-api \
  --min-instances=0 \
  --region=asia-northeast1
```

### 2. 优化镜像大小

```bash
# 检查镜像大小
docker image ls

# 使用多阶段构建来减小镜像大小
# 已在 Dockerfile 中优化
```

### 3. 选择经济的区域

- **asia-northeast1**（东京）：$0.00002057 per vCPU-second
- **us-central1**（爱荷华）：$0.00001667 per vCPU-second

### 4. 监控成本

```bash
# 设置预算警报
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Cloud Run Budget" \
  --budget-amount=100 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

## ❓ 常见问题

### Q1: 如何增加内存解决超时问题？

```bash
gcloud run deploy jplatpat-api \
  --memory=4Gi \
  --timeout=900
```

### Q2: 如何查看请求错误？

```bash
# 查看最后 100 行日志
gcloud run logs read jplatpat-api \
  --region=asia-northeast1 \
  --limit=100

# 过滤错误日志
gcloud run logs read jplatpat-api \
  --region=asia-northeast1 \
  --limit=100 | grep ERROR
```

### Q3: 如何删除部署的服务？

```bash
gcloud run services delete jplatpat-api \
  --region=asia-northeast1 \
  --quiet
```

### Q4: 如何在多个区域部署？

```bash
# 部署到多个区域
for region in asia-northeast1 us-central1 europe-west1; do
  bash deploy-cloudrun.sh $PROJECT_ID $region
done
```

### Q5: 如何使用自定义域名？

```bash
# 在 Cloud Run 控制面板中：
# 1. 选择服务
# 2. 点击"设置自定义域"
# 3. 添加您的域名
# 4. 按照 DNS 配置说明操作
```

## 📚 相关文档

- [Cloud Run 官方文档](https://cloud.google.com/run/docs)
- [Cloud Run 定价](https://cloud.google.com/run/pricing)
- [Cloud Run 最佳实践](https://cloud.google.com/run/docs/quickstarts/build-and-deploy)
- [GitHub Secrets 配置](./GITHUB_SECRETS_SETUP.md)
- [详细部署指南](./CLOUD_RUN_DEPLOY.md)

## 🆘 获取支持

遇到问题？

1. **查看日志**
   ```bash
   gcloud run logs read jplatpat-api --follow
   ```

2. **查阅文档**
   - [Cloud Run 故障排除](https://cloud.google.com/run/docs/troubleshooting)
   - [Playwright 常见问题](https://playwright.dev/python/docs/troubleshooting)

3. **Stack Overflow**
   - 标签：`google-cloud-run`, `playwright`, `python`

4. **Google Cloud Support**
   - 对于付费的 GCP 账户，可以创建支持工单

---

**祝您部署顺利！** 🎉
