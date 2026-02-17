#!/bin/bash

# Configuration - Change these to match your GCP project
PROJECT_ID="schul-ag-portal-gechingen"
REGION="europe-west3" # Frankfurt
SERVICE_NAME="schul-ag-portal"

echo "🚀 Starting Deployment for $SERVICE_NAME to Google Cloud Run..."

# 1. Enable necessary services
echo "📦 Enabling GCP Services..."
gcloud services enable run.googleapis.com \
                       sqladmin.googleapis.com \
                       artifactregistry.googleapis.com \
                       secretmanager.googleapis.com

# 2. Build and Push Image using Cloud Build (no local Docker needed)
echo "🏗️ Building Container Image via Cloud Build..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 3. Deploy to Cloud Run
# Note: This assumes you have already set up a Cloud SQL instance and 
# added the DB connection string to Secret Manager.
echo "🚢 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --update-env-vars DEBUG=False,ALLOWED_HOSTS=*

echo "✅ Deployment finished!"
echo "📎 Service URL: $(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')"
