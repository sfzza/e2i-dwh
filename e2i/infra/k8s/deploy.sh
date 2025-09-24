#!/bin/bash

# Datawarehouse Kubernetes Deployment Script
# This script deploys the datawarehouse application to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if kustomize is installed
if ! command -v kustomize &> /dev/null; then
    print_warning "kustomize is not installed. Installing kustomize..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install kustomize
    else
        print_error "Please install kustomize manually for your OS"
        exit 1
    fi
fi

# Function to apply manifests
apply_manifests() {
    local environment=$1
    
    print_status "Applying manifests for environment: $environment"
    
    if [ "$environment" == "railway" ]; then
        kustomize build railway | kubectl apply -f -
    else
        kustomize build base | kubectl apply -f -
    fi
    
    if [ $? -eq 0 ]; then
        print_status "Manifests applied successfully"
    else
        print_error "Failed to apply manifests"
        exit 1
    fi
}

# Function to wait for deployments
wait_for_deployments() {
    print_status "Waiting for deployments to be ready..."
    
    # Wait for database deployments
    kubectl wait --for=condition=available --timeout=300s deployment/airflow-postgres -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/orchestrator-postgres -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/tokenization-postgres -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/metabase-postgres -n datawarehouse
    
    # Wait for core services
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/clickhouse -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/minio -n datawarehouse
    
    # Wait for tokenization service
    kubectl wait --for=condition=available --timeout=300s deployment/tokenization-service -n datawarehouse
    
    # Wait for orchestrator
    kubectl wait --for=condition=available --timeout=300s deployment/orchestrator -n datawarehouse
    
    # Wait for Django services
    kubectl wait --for=condition=available --timeout=300s deployment/django -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/reporting -n datawarehouse
    
    # Wait for Airflow (after init job completes)
    print_status "Waiting for Airflow initialization..."
    kubectl wait --for=condition=complete --timeout=300s job/airflow-init -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/airflow-webserver -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/airflow-scheduler -n datawarehouse
    
    # Wait for frontend and metabase
    kubectl wait --for=condition=available --timeout=300s deployment/frontend -n datawarehouse
    kubectl wait --for=condition=available --timeout=300s deployment/metabase -n datawarehouse
    
    print_status "All deployments are ready!"
}

# Function to show status
show_status() {
    print_status "Deployment Status:"
    kubectl get pods -n datawarehouse
    echo
    print_status "Services:"
    kubectl get services -n datawarehouse
    echo
    print_status "Ingress:"
    kubectl get ingress -n datawarehouse
}

# Main deployment function
deploy() {
    local environment=${1:-base}
    
    print_status "Starting deployment for environment: $environment"
    
    # Apply manifests
    apply_manifests $environment
    
    # Wait for deployments
    wait_for_deployments
    
    # Show status
    show_status
    
    print_status "Deployment completed successfully!"
    print_status "You can access the services using port-forwarding:"
    print_status "  Frontend: kubectl port-forward service/frontend 8080:80 -n datawarehouse"
    print_status "  Airflow: kubectl port-forward service/airflow-webserver 8081:8080 -n datawarehouse"
    print_status "  Django API: kubectl port-forward service/django 8082:8001 -n datawarehouse"
    print_status "  Metabase: kubectl port-forward service/metabase 8083:3000 -n datawarehouse"
}

# Function to clean up
cleanup() {
    print_status "Cleaning up deployment..."
    kubectl delete namespace datawarehouse --ignore-not-found=true
    print_status "Cleanup completed!"
}

# Parse command line arguments
case "$1" in
    "deploy")
        deploy $2
        ;;
    "cleanup")
        cleanup
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 {deploy|cleanup|status} [environment]"
        echo "  deploy [base|railway] - Deploy the application"
        echo "  cleanup               - Clean up the deployment"
        echo "  status                - Show deployment status"
        exit 1
        ;;
esac
