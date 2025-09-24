#!/bin/bash

# Setup Git repository and push to GitHub
set -e

echo "Setting up Git repository for e2i-dwh..."

# Navigate to the project directory
cd /Users/dominicsu/Downloads/datawarehouse

# Initialize git repository if it doesn't exist
if [ ! -d ".git" ]; then
    echo "Initializing Git repository..."
    git init
fi

# Add remote origin
echo "Adding remote origin..."
git remote add origin https://github.com/sfzza/e2i-dwh.git || git remote set-url origin https://github.com/sfzza/e2i-dwh.git

# Add all files
echo "Adding all files..."
git add .

# Commit the changes
echo "Committing changes..."
git commit -m "Initial commit: Docker Compose to Kubernetes migration

- Migrated all 12 services from Docker Compose to Kubernetes
- Created Railway-optimized Kubernetes manifests
- Added comprehensive documentation and deployment scripts
- Includes: Airflow, Django, Frontend, Metabase, ClickHouse, Redis, MinIO, PostgreSQL instances
- Ready for Railway deployment"

# Push to GitHub
echo "Pushing to GitHub..."
git branch -M main
git push -u origin main

echo "Successfully pushed to https://github.com/sfzza/e2i-dwh.git"
echo "Repository is now available at: https://github.com/sfzza/e2i-dwh"
