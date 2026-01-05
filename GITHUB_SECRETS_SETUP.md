# GitHub Secrets 配置指南

本文档说明如何为 GitHub Actions 配置 Cloud Run 自动部署所需的 Secrets。

## 快速开始

### 方法 1：使用工作身份联合（Workload Identity Federation）- 推荐

这是最安全的方式，无需长期有效的密钥。

#### Step 1: 创建服务账户

```bash
# 设置变量
export PROJECT_ID=your-project-id
export SERVICE_ACCOUNT_NAME=github-actions-sa

# 创建服务账户
gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
  --display-name="GitHub Actions Service Account"

# 获取服务账户邮箱
export SERVICE_ACCOUNT_EMAIL=${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
echo $SERVICE_ACCOUNT_EMAIL
```

#### Step 2: 授予必要权限

```bash
# Cloud Run 部署权限
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/run.admin"

# Artifact Registry 权限
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Cloud Build 权限
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/cloudbuild.builds.editor"

# Service Account 用户权限
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/iam.serviceAccountUser"
```

#### Step 3: 配置工作身份联合

```bash
# 设置 GitHub repo 信息
export GITHUB_REPO=ShouyiTian/kirin-jplatpat
export GITHUB_ORG=ShouyiTian

# 创建工作身份提供程序池
gcloud iam workload-identity-pools create github-pool \
  --project=${PROJECT_ID} \
  --location=global \
  --display-name=github-pool

# 获取池资源名称
export WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools \
  --project=${PROJECT_ID} \
  --location=global \
  list --format="value(name)" --filter="displayName:github-pool")

echo "Workload Identity Pool ID: $WORKLOAD_IDENTITY_POOL_ID"

# 创建工作身份提供程序
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project=${PROJECT_ID} \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name=github-provider \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.aud=assertion.aud,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'" \
  --disabled=false

# 获取提供程序资源名称
export WORKLOAD_IDENTITY_PROVIDER=$(gcloud iam workload-identity-pools \
  providers list \
  --project=${PROJECT_ID} \
  --location=global \
  --workload-identity-pool=github-pool \
  --format="value(name)")

echo "Workload Identity Provider: $WORKLOAD_IDENTITY_PROVIDER"
```

#### Step 4: 配置服务账户的身份绑定

```bash
# 允许 GitHub Actions 模拟服务账户
gcloud iam service-accounts add-iam-policy-binding ${SERVICE_ACCOUNT_EMAIL} \
  --project=${PROJECT_ID} \
  --role=roles/iam.workloadIdentityUser \
  --condition='resource.matchTag("iam.googleapis.com/github_repository", "'${GITHUB_REPO}'")' \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_PROVIDER}/attribute.repository/${GITHUB_REPO}"
```

#### Step 5: 添加 GitHub Secrets

在 GitHub 仓库设置中添加以下 Secrets：

```
Settings > Secrets and variables > Actions > New repository secret
```

添加以下密钥：

| 名称 | 值 | 说明 |
|-----|-----|-----|
| `GCP_PROJECT_ID` | your-project-id | 您的 GCP 项目 ID |
| `WIF_PROVIDER` | $WORKLOAD_IDENTITY_PROVIDER | 工作身份提供程序资源名称 |
| `WIF_SERVICE_ACCOUNT` | $SERVICE_ACCOUNT_EMAIL | 服务账户邮箱 |

**示例 WIF_PROVIDER 值**：
```
projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

### 方法 2：使用服务账户密钥

**⚠️ 较少推荐** - 这种方法使用长期有效的密钥，安全性相对较低。

#### Step 1: 创建服务账户和密钥

```bash
# 创建服务账户
gcloud iam service-accounts create github-actions-sa

# 创建密钥
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-sa@PROJECT_ID.iam.gserviceaccount.com
```

#### Step 2: 授予权限

```bash
# 授予 Cloud Run Admin 角色
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:github-actions-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# 授予 Artifact Registry Writer 角色
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:github-actions-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# 授予 Cloud Build Editor 角色
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:github-actions-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"
```

#### Step 3: 添加 GitHub Secrets

```
Settings > Secrets and variables > Actions > New repository secret
```

| 名称 | 值 |
|-----|-----|
| `GCP_PROJECT_ID` | 您的项目 ID |
| `GCP_SA_KEY` | key.json 的内容 |

## 在 GitHub 中添加 Secrets

### 通过 GitHub 网页界面

1. 打开您的仓库
2. 进入 **Settings > Secrets and variables > Actions**
3. 点击 **New repository secret**
4. 输入名称和值
5. 点击 **Add secret**

### 通过 GitHub CLI

```bash
gh secret set GCP_PROJECT_ID --body "your-project-id"
gh secret set WIF_PROVIDER --body "projects/.../providers/github-provider"
gh secret set WIF_SERVICE_ACCOUNT --body "sa@project.iam.gserviceaccount.com"
```

## 验证配置

```bash
# 列出 Secrets（不显示值）
gh secret list

# 测试 GitHub Actions 工作流
# 推送代码到 main 分支以触发部署工作流
```

## 故障排除

### 问题：GitHub Actions 认证失败

**症状**：Workload Identity 或 service account key 认证失败

**解决方案**：
```bash
# 验证服务账户权限
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"

# 验证工作身份提供程序配置
gcloud iam workload-identity-pools describe github-pool \
  --location=global --project=PROJECT_ID
```

### 问题：Cloud Run 部署权限不足

**症状**：`PermissionDenied: User is not authorized to perform: run.services.create`

**解决方案**：
```bash
# 确保服务账户有所有必要权限
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/run.admin"
```

## 安全最佳实践

1. **使用工作身份联合（推荐）**
   - 不需要存储长期密钥
   - 自动轮换
   - 更安全的令牌管理

2. **限制服务账户权限**
   ```bash
   # 只授予必要的角色，避免使用 Editor 或 Owner 角色
   roles/run.admin          # Cloud Run 部署
   roles/artifactregistry.writer  # 镜像推送
   roles/cloudbuild.builds.editor # 容器构建
   ```

3. **定期审计**
   ```bash
   # 列出服务账户的所有角色
   gcloud projects get-iam-policy PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:*" \
     --format="table(bindings.role)"
   ```

4. **轮换密钥（使用方法2时）**
   ```bash
   # 定期更换密钥（建议每 3-6 个月）
   gcloud iam service-accounts keys list \
     --iam-account=github-actions-sa@PROJECT_ID.iam.gserviceaccount.com
   
   # 删除旧密钥
   gcloud iam service-accounts keys delete KEY_ID \
     --iam-account=github-actions-sa@PROJECT_ID.iam.gserviceaccount.com
   ```

## 清理资源

如需删除已配置的资源：

```bash
# 删除服务账户
gcloud iam service-accounts delete github-actions-sa@PROJECT_ID.iam.gserviceaccount.com

# 删除工作身份池（如使用方法1）
gcloud iam workload-identity-pools delete github-pool \
  --location=global --project=PROJECT_ID
```

## 更多信息

- [Google Cloud Workload Identity Federation](https://cloud.google.com/docs/authentication/workload-identity-federation)
- [GitHub Actions Google Cloud Authentication](https://github.com/google-github-actions/auth)
- [Cloud Run IAM Roles](https://cloud.google.com/run/docs/deploying/identity-based-access)
