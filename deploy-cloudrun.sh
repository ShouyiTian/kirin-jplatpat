#!/bin/bash
set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${1:-}"
REGION="${2:-asia-northeast1}"  # Tokyo region
SERVICE_NAME="${3:-jplatpat-api}"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: PROJECT_ID is required${NC}"
    echo "Usage: ./deploy-cloudrun.sh <PROJECT_ID> [REGION] [SERVICE_NAME]"
    echo ""
    echo "Examples:"
    echo "  ./deploy-cloudrun.sh my-gcp-project"
    echo "  ./deploy-cloudrun.sh my-gcp-project asia-northeast1 jplatpat-api"
    exit 1
fi

echo -e "${YELLOW}=== Cloud Run Deployment ===${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"
echo ""

# Step 1: Check gcloud CLI
echo -e "${YELLOW}1. Checking gcloud CLI...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}gcloud CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo -e "${GREEN}✓ gcloud CLI found${NC}"
echo ""

# Step 2: Set project
echo -e "${YELLOW}2. Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✓ Project set to $PROJECT_ID${NC}"
echo ""

# Step 3: Enable required APIs
echo -e "${YELLOW}3. Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Step 4: Build and push image
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$SERVICE_NAME/$SERVICE_NAME"

echo -e "${YELLOW}4. Creating Artifact Registry repository (if not exists)...${NC}"
gcloud artifacts repositories create $SERVICE_NAME \
  --repository-format=docker \
  --location=$REGION \
  --quiet || echo "Repository already exists"
echo -e "${GREEN}✓ Repository ready${NC}"
echo ""

echo -e "${YELLOW}5. Building and pushing Docker image...${NC}"
echo "Image: $IMAGE_NAME:latest"
gcloud builds submit \
  --tag $IMAGE_NAME:latest \
  --region=$REGION
echo -e "${GREEN}✓ Image built and pushed${NC}"
echo ""

# Step 5: Deploy to Cloud Run
echo -e "${YELLOW}6. Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_NAME:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=10 \
  --port=8000
echo -e "${GREEN}✓ Service deployed${NC}"
echo ""

# Step 6: Get service URL
echo -e "${YELLOW}7. Getting service details...${NC}"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')
echo -e "${GREEN}✓ Service URL: $SERVICE_URL${NC}"
echo ""

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "You can now access your API at:"
echo "  $SERVICE_URL"
echo ""
echo "Try the API documentation:"
echo "  $SERVICE_URL/docs"
echo ""
echo "Search endpoint:"
echo "  curl -X POST '$SERVICE_URL/search' \\"
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{
echo '      "query": "人工知能",
echo '      "limit": 10,
echo '      "timeout": 20000,
echo '      "fetch_abstract": true,
echo '      "headless": true
echo '    }'"'"
echo ""

# Optional: View logs
echo -e "${YELLOW}To view service logs:${NC}"
echo "  gcloud run logs read $SERVICE_NAME --region=$REGION --limit=50"
echo ""

# Optional: Clean up old images
echo -e "${YELLOW}To clean up old images:${NC}"
echo "  gcloud artifacts docker images list $REGION-docker.pkg.dev/$PROJECT_ID/$SERVICE_NAME"
