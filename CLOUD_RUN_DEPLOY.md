# Cloud Run 部署指南

本指南将帮助您将 J-PlatPat Search API 部署到 Google Cloud Run。

## 前置条件

1. **Google Cloud Project**
   - 创建 GCP 项目: https://console.cloud.google.com
   - 记下您的 Project ID

2. **安装工具**
   ```bash
   # 安装 Google Cloud SDK
   # macOS
   brew install --cask google-cloud-sdk
   
   # Linux
   curl https://sdk.cloud.google.com | bash
   
   # Windows
   # 下载安装程序: https://cloud.google.com/sdk/docs/install
   ```

3. **初始化 gcloud**
   ```bash
   gcloud init
   gcloud auth login
   ```

## 快速部署方法

### 方法 1：使用部署脚本（推荐）

```bash
# 进入项目目录
cd /workspaces/kirin-jplatpat

# 赋予脚本执行权限
chmod +x deploy-cloudrun.sh

# 执行部署脚本
./deploy-cloudrun.sh YOUR_GCP_PROJECT_ID

# 或指定区域和服务名称
./deploy-cloudrun.sh YOUR_GCP_PROJECT_ID asia-northeast1 jplatpat-api
```

脚本会自动：
- 检查 gcloud CLI
- 设置 GCP 项目
- 启用必要的 API
- 构建 Docker 镜像
- 推送到 Artifact Registry
- 部署到 Cloud Run

### 方法 2：手动部署

#### Step 1: 启用必要的 API

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

#### Step 2: 创建 Artifact Registry 仓库

```bash
gcloud artifacts repositories create jplatpat-api \
  --repository-format=docker \
  --location=asia-northeast1
```

#### Step 3: 构建和推送 Docker 镜像

```bash
# 设置项目
export PROJECT_ID=your-project-id
export REGION=asia-northeast1
export SERVICE_NAME=jplatpat-api

# 构建镜像
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest \
  --region=${REGION}
```

#### Step 4: 部署到 Cloud Run

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=10 \
  --port=8000
```

## 部署配置说明

| 配置项 | 值 | 说明 |
|------|-----|-----|
| Memory | 2Gi | 为 Playwright 浏览器分配足够内存 |
| CPU | 2 | 处理并发请求 |
| Timeout | 600s | 长期爬取操作的超时时间 |
| Max Instances | 10 | 自动扩展的最大实例数 |
| Port | 8000 | API 服务端口 |

## 验证部署

部署完成后，您可以：

### 1. 获取服务 URL

```bash
gcloud run services describe jplatpat-api \
  --region=asia-northeast1 \
  --format='value(status.url)'
```

### 2. 访问 API 文档

打开浏览器访问：`https://your-service-url.run.app/docs`

### 3. 测试 API

```bash
SERVICE_URL=$(gcloud run services describe jplatpat-api \
  --region=asia-northeast1 \
  --format='value(status.url)')

curl -X POST "${SERVICE_URL}/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工知能",
    "limit": 5,
    "timeout": 20000,
    "fetch_abstract": true,
    "headless": true
  }'
```

### 4. 查看实时日志

```bash
gcloud run logs read jplatpat-api \
  --region=asia-northeast1 \
  --limit=50
  --follow
```

## 成本优化建议

1. **使用区域就近原则**
   - 日本用户：`asia-northeast1`（东京）
   - 美国用户：`us-central1`（爱荷华）
   - 欧洲用户：`europe-west1`（比利时）

2. **调整自动扩展**
   ```bash
   gcloud run deploy jplatpat-api \
     --min-instances=0 \
     --max-instances=5  # 根据需要调整
   ```

3. **设置并发数限制**
   ```bash
   gcloud run deploy jplatpat-api \
     --concurrency=50  # 每个实例最多 50 个并发请求
   ```

## 常见问题

### Q1: 部署后返回 500 错误

**原因**：Playwright 可能在 Cloud Run 容器中失败

**解决方案**：
```bash
# 查看日志
gcloud run logs read jplatpat-api --limit=100

# 增加内存和超时
gcloud run deploy jplatpat-api \
  --memory=4Gi \
  --timeout=900
```

### Q2: 镜像构建失败

**原因**：Artifact Registry 权限或网络问题

**解决方案**：
```bash
# 验证权限
gcloud auth application-default login

# 重试构建
gcloud builds submit --retry
```

### Q3: 如何更新已部署的服务

```bash
# 1. 修改代码
# 2. 推送到 GitHub
# 3. 重新构建和部署
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest

# 或重新部署最新镜像
gcloud run deploy ${SERVICE_NAME} \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest
```

### Q4: 如何删除服务

```bash
gcloud run services delete jplatpat-api \
  --region=asia-northeast1 \
  --quiet
```

## 环境变量配置

如果需要在 Cloud Run 中设置环境变量：

```bash
gcloud run deploy jplatpat-api \
  --set-env-vars KEY1=value1,KEY2=value2
```

## 持续部署（CI/CD）

### 使用 GitHub Actions

在 `.github/workflows/deploy-cloudrun.yml` 中创建：

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: asia-northeast1
  SERVICE_NAME: jplatpat-api

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v3
      
      - uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - uses: google-github-actions/cloud-cli@v1
      
      - name: Build and Push
        run: |
          gcloud builds submit \
            --tag ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}/${{ env.SERVICE_NAME }}:${{ github.sha }}
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --image=${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            --region=${{ env.REGION }}
```

## 监控和告警

### 设置监控

```bash
# 查看服务指标
gcloud monitoring dashboards list

# 创建告警（推荐使用 Google Cloud Console）
# https://console.cloud.google.com/monitoring/alerting
```

### 关键指标

- **Request Latency**：API 响应时间
- **Error Rate**：错误请求比例
- **CPU Utilization**：CPU 使用率
- **Memory Usage**：内存使用率

## 预算告警

```bash
# 在 Google Cloud Console 设置
# https://console.cloud.google.com/billing/budgets
```

建议：
- 设置每月预算告警（例如 $100）
- 启用成本优化建议

## 更多信息

- [Cloud Run 官方文档](https://cloud.google.com/run/docs)
- [Cloud Run 定价](https://cloud.google.com/run/pricing)
- [构建容器镜像](https://cloud.google.com/run/docs/quickstarts/build-and-deploy)

## 支持

如有问题，请查看：
- Cloud Run 日志：`gcloud run logs read`
- GCP 文档：https://cloud.google.com/docs
- Stack Overflow：标签 `google-cloud-run`
