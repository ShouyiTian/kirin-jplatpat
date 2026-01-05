# ⚡ 快速部署指南

您的项目已完全准备好部署到 Google Cloud Run。

## 当前状态：✅ 已就绪

```
✅ Dockerfile 已配置
✅ api.py 已优化
✅ 部署脚本已准备
✅ 所有文件已提交到 GitHub
```

## 部署方式（二选一）

### 方式 1️⃣ : 使用 Google Cloud Console（最简单）

**步骤：**

1. 打开 Google Cloud Console
   - https://console.cloud.google.com

2. 在搜索栏中搜索 **"Cloud Run"**

3. 点击 **"创建服务"**

4. 选择 **"从源代码部署"**

5. 按以下配置填写：
   ```
   代码库：ShouyiTian/kirin-jplatpat
   分支：main
   构建类型：Dockerfile
   区域：asia-northeast1（东京）
   ```

6. 点击 **"部署"**，等待完成即可

### 方式 2️⃣ : 使用命令行

**前置条件：**
```bash
# 安装 Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# 认证
gcloud auth login

# 设置项目
gcloud config set project 588661622774
```

**执行部署：**
```bash
cd /workspaces/kirin-jplatpat
bash deploy-cloudrun.sh 588661622774 asia-northeast1
```

### 方式 3️⃣ : 自动 CI/CD（GitHub Actions）

配置 GitHub Secrets 后，每次推送到 main 分支都会自动部署。

参考：`GITHUB_SECRETS_SETUP.md`

---

## 部署后

### 1. 获取服务 URL
```bash
gcloud run services describe jplatpat-api \
  --region=asia-northeast1 \
  --format='value(status.url)'
```

### 2. 测试 API
```bash
# 访问 Swagger 文档
https://your-service-url.run.app/docs

# 或测试搜索
curl -X POST 'https://your-service-url.run.app/search' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "人工知能",
    "limit": 5,
    "timeout": 20000,
    "fetch_abstract": true
  }'
```

### 3. 查看日志
```bash
gcloud run logs read jplatpat-api \
  --region=asia-northeast1 \
  --follow
```

---

## 项目 ID：588661622774

## 推荐区域

- **asia-northeast1**（东京）- 推荐日本用户
- **us-central1**（美国） - 推荐美国用户  
- **europe-west1**（比利时）- 推荐欧洲用户

---

## 资源配置

- **内存**：2Gi（Playwright 优化）
- **CPU**：2 核
- **超时**：600 秒
- **最大实例**：10 个
- **最小实例**：0 个（按需启动）

---

## 更多帮助

- 详细部署指南：`CLOUDRUN_QUICKSTART.md`
- GitHub Secrets 配置：`GITHUB_SECRETS_SETUP.md`
- 完整部署说明：`CLOUD_RUN_DEPLOY.md`

**祝您部署顺利！** 🚀
