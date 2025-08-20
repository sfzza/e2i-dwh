#!/bin/bash
# Run Django migrations
python backend/manage.py makemigrations
python backend/manage.py migrate
