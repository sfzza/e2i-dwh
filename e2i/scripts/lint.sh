#!/bin/bash
# Run linters and formatters
echo "Running flake8..."
flake8 backend
echo "Running black..."
black backend
