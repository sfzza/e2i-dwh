#!/bin/bash
# Initialize dev environment
echo "Setting up dev environment..."
pip install -r backend/requirements/dev.txt
docker-compose -f ../docker-compose.yml up -d db
python backend/manage.py migrate
echo "✅ Dev environment ready."
