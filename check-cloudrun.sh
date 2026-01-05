#!/bin/bash

# Cloud Run 部署前检查脚本

set -e

echo "🔍 Cloud Run 部署前检查..."
echo ""

# 检查 gcloud CLI
echo "1️⃣  检查 gcloud CLI..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ 错误：gcloud CLI 未安装"
    echo "   请访问: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo "✅ gcloud CLI 已安装"
echo ""

# 检查 docker
echo "2️⃣  检查 Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ 错误：Docker 未安装"
    echo "   请访问: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker 已安装"
echo ""

# 检查认证
echo "3️⃣  检查 Google Cloud 认证..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
    echo "❌ 错误：未登录 Google Cloud"
    echo "   运行: gcloud auth login"
    exit 1
fi
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
echo "✅ 已认证: $ACCOUNT"
echo ""

# 检查项目设置
echo "4️⃣  检查项目设置..."
PROJECT=$(gcloud config get-value project)
if [ -z "$PROJECT" ]; then
    echo "❌ 错误：未设置 GCP 项目"
    echo "   运行: gcloud config set project PROJECT_ID"
    exit 1
fi
echo "✅ 项目: $PROJECT"
echo ""

# 检查 Dockerfile
echo "5️⃣  检查 Dockerfile..."
if [ ! -f "Dockerfile" ]; then
    echo "❌ 错误：Dockerfile 不存在"
    exit 1
fi
echo "✅ Dockerfile 存在"
echo ""

# 检查必要的 Python 文件
echo "6️⃣  检查应用文件..."
if [ ! -f "api.py" ]; then
    echo "❌ 错误：api.py 不存在"
    exit 1
fi
echo "✅ api.py 存在"

if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误：requirements.txt 不存在"
    exit 1
fi
echo "✅ requirements.txt 存在"
echo ""

# 检查 API 健康端点
echo "7️⃣  检查 API 健康端点..."
if ! grep -q "/health" api.py; then
    echo "⚠️  警告：api.py 中未找到 /health 端点"
    echo "   建议添加健康检查端点以支持 Cloud Run 监控"
fi
echo "✅ API 结构检查完成"
echo ""

# 检查所需的 API
echo "8️⃣  检查所需的 GCP APIs..."
REQUIRED_APIS=("cloudbuild.googleapis.com" "run.googleapis.com" "artifactregistry.googleapis.com")
for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" &>/dev/null; then
        echo "✅ $api 已启用"
    else
        echo "⚠️  $api 未启用，将在部署时自动启用"
    fi
done
echo ""

# 本地构建测试
echo "9️⃣  本地 Docker 构建测试 (可选)..."
read -p "是否进行本地构建测试? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔨 构建 Docker 镜像..."
    if docker build -t jplatpat-api:test .; then
        echo "✅ 本地构建成功"
        docker rmi jplatpat-api:test
    else
        echo "❌ 本地构建失败"
        exit 1
    fi
else
    echo "⏭️  跳过本地构建测试"
fi
echo ""

echo "✅ 所有检查完成！"
echo ""
echo "📋 部署信息摘要："
echo "   - GCP 项目: $PROJECT"
echo "   - 认证用户: $ACCOUNT"
echo "   - Docker: $(docker --version)"
echo "   - gcloud: $(gcloud --version | head -1)"
echo ""
echo "🚀 准备就绪，可以开始部署！"
echo ""
echo "运行部署："
echo "  ./deploy-cloudrun.sh $PROJECT"
