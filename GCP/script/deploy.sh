#!/bin/bash

# Build the Docker image
docker build -t gcp-script .

# Tag the image for GCP Container Registry
docker tag gcp-script gcr.io/$(gcloud config get-value project)/gcp-script

# Push the image to GCP Container Registry
docker push gcr.io/$(gcloud config get-value project)/gcp-script

# Deploy to Cloud Run
gcloud run deploy gcp-script \
  --image gcr.io/$(gcloud config get-value project)/gcp-script \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated 