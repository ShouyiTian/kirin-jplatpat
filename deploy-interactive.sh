#!/bin/bash

# 交互式 Cloud Run 部署脚本

set -e

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   J-PlatPat API - Cloud Run 部署                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Step 1: 获取项目 ID
echo "📋 Step 1: 获取 GCP 项目信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "请在 Google Cloud Console 中："
echo "  1. 访问 https://console.cloud.google.com"
echo "  2. 在顶部栏找到项目 ID（格式：abc-123-xyz）"
echo ""

read -p "请输入您的 GCP 项目 ID: " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo "❌ 错误：项目 ID 不能为空"
    exit 1
fi

echo "✅ 项目 ID: $PROJECT_ID"
echo ""

# Step 2: 设置项目
echo "🔧 Step 2: 设置 gcloud 项目"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
gcloud config set project $PROJECT_ID
echo "✅ 项目已设置"
echo ""

# Step 3: 登录
echo "🔐 Step 3: Google Cloud 认证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "正在打开浏览器进行认证..."
echo "（如果浏览器没有打开，请访问下面的链接）"
echo ""

gcloud auth login --no-launch-browser

if [ $? -ne 0 ]; then
    echo "❌ 认证失败"
    exit 1
fi

echo ""
echo "✅ 认证成功"
echo ""

# Step 4: 选择区域
echo "🌍 Step 4: 选择部署区域"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "推荐区域："
echo "  1) asia-northeast1 (东京) - 推荐日本用户"
echo "  2) us-central1 (美国) - 推荐美国用户"
echo "  3) europe-west1 (比利时) - 推荐欧洲用户"
echo ""

read -p "请选择区域 (1-3，默认 1): " region_choice
region_choice=${region_choice:-1}

case $region_choice in
    1) REGION="asia-northeast1" ;;
    2) REGION="us-central1" ;;
    3) REGION="europe-west1" ;;
    *) REGION="asia-northeast1" ;;
esac

echo "✅ 选择区域: $REGION"
echo ""

# Step 5: 启用 API
echo "⚙️  Step 5: 启用必要的 GCP APIs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "正在启用 Cloud Build, Cloud Run 和 Artifact Registry..."

gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable artifactregistry.googleapis.com --quiet

echo "✅ APIs 已启用"
echo ""

# Step 6: 创建 Artifact Registry 仓库
echo "📦 Step 6: 创建 Artifact Registry 仓库"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "正在创建容器仓库..."

gcloud artifacts repositories create jplatpat-api \
  --repository-format=docker \
  --location=$REGION \
  --quiet 2>/dev/null || echo "仓库已存在，继续..."

echo "✅ 仓库就绪"
echo ""

# Step 7: 构建和部署
echo "🔨 Step 7: 构建和推送 Docker 镜像"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "这可能需要 5-10 分钟，请耐心等待..."
echo ""

IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/jplatpat-api/jplatpat-api"

gcloud builds submit \
  --tag $IMAGE_NAME:latest \
  --region=$REGION

echo "✅ 镜像已构建并推送"
echo ""

# Step 8: 部署到 Cloud Run
echo "🚀 Step 8: 部署到 Cloud Run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "正在部署服务..."

gcloud run deploy jplatpat-api \
  --image=$IMAGE_NAME:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=10 \
  --port=8000 \
  --quiet

echo "✅ 服务已部署"
echo ""

# Step 9: 获取服务 URL
echo "📍 Step 9: 获取服务 URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SERVICE_URL=$(gcloud run services describe jplatpat-api \
  --region=$REGION \
  --format='value(status.url)')

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║              ✅ 部署成功！                             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📌 服务信息："
echo "   服务名称: jplatpat-api"
echo "   区域: $REGION"
echo "   项目 ID: $PROJECT_ID"
echo ""
echo "🌐 API URL:"
echo "   $SERVICE_URL"
echo ""
echo "📖 API 文档（Swagger UI）:"
echo "   $SERVICE_URL/docs"
echo ""
echo "🔍 测试搜索功能:"
echo "   curl -X POST '$SERVICE_URL/search' \\"
echo '     -H "Content-Type: application/json" \'
echo "     -d '{\"query\": \"人工知能\", \"limit\": 5}'"
echo ""
echo "💚 查看实时日志:"
echo "   gcloud run logs read jplatpat-api --region=$REGION --follow"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 后续步骤："
echo ""
echo "1. 访问 API 文档测试："
echo "   打开浏览器: $SERVICE_URL/docs"
echo ""
echo "2. 查看日志："
echo "   gcloud run logs read jplatpat-api --region=$REGION --follow"
echo ""
echo "3. 更新部署（修改代码后）："
echo "   bash deploy-cloudrun.sh $PROJECT_ID $REGION"
echo ""
echo "4. 删除服务（如果需要）："
echo "   gcloud run services delete jplatpat-api --region=$REGION --quiet"
echo ""
