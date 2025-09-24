#!/bin/bash

# Railway Kubernetes Deployment Script
# Quick deployment script for Railway platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    if ! command -v kustomize &> /dev/null; then
        print_error "kustomize is not installed. Please install kustomize first."
        print_status "Install with: brew install kustomize (macOS) or visit https://kustomize.io/"
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubectl configuration."
        exit 1
    fi
    
    print_status "Prerequisites check passed!"
}

# Deploy to Railway
deploy_to_railway() {
    print_header "Deploying to Railway"
    
    print_status "Applying Railway-specific configuration..."
    
    # Apply the Railway kustomization
    kustomize build railway | kubectl apply -f -
    
    if [ $? -eq 0 ]; then
        print_status "Manifests applied successfully!"
    else
        print_error "Failed to apply manifests"
        exit 1
    fi
}

# Wait for critical services
wait_for_critical_services() {
    print_header "Waiting for Critical Services"
    
    print_status "Waiting for databases to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/orchestrator-postgres -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/airflow-postgres -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/tokenization-postgres -n datawarehouse || true
    
    print_status "Waiting for core services..."
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/clickhouse -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/minio -n datawarehouse || true
    
    print_status "Waiting for application services..."
    kubectl wait --for=condition=available --timeout=300s deployment/tokenization-service -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/orchestrator -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/django -n datawarehouse || true
    
    print_status "Waiting for Airflow initialization..."
    kubectl wait --for=condition=complete --timeout=300s job/airflow-init -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/airflow-webserver -n datawarehouse || true
    
    print_status "Waiting for frontend services..."
    kubectl wait --for=condition=available --timeout=300s deployment/frontend -n datawarehouse || true
    kubectl wait --for=condition=available --timeout=300s deployment/metabase -n datawarehouse || true
}

# Show deployment status
show_status() {
    print_header "Deployment Status"
    
    print_status "Pods:"
    kubectl get pods -n datawarehouse
    
    echo
    print_status "Services:"
    kubectl get services -n datawarehouse
    
    echo
    print_status "Ingress:"
    kubectl get ingress -n datawarehouse || print_warning "No ingress found - this is normal if not configured"
}

# Show access information
show_access_info() {
    print_header "Access Information"
    
    print_status "To access your services locally, use port-forwarding:"
    echo
    echo -e "${GREEN}Frontend:${NC}"
    echo "  kubectl port-forward service/frontend 8080:80 -n datawarehouse"
    echo "  Then visit: http://localhost:8080"
    echo
    echo -e "${GREEN}Django API:${NC}"
    echo "  kubectl port-forward service/django 8081:8001 -n datawarehouse"
    echo "  Then visit: http://localhost:8081"
    echo
    echo -e "${GREEN}Airflow:${NC}"
    echo "  kubectl port-forward service/airflow-webserver 8082:8080 -n datawarehouse"
    echo "  Then visit: http://localhost:8082 (admin: airflow/airflow)"
    echo
    echo -e "${GREEN}Metabase:${NC}"
    echo "  kubectl port-forward service/metabase 8083:3000 -n datawarehouse"
    echo "  Then visit: http://localhost:8083"
    echo
    echo -e "${GREEN}Orchestrator:${NC}"
    echo "  kubectl port-forward service/orchestrator 8084:8002 -n datawarehouse"
    echo "  Then visit: http://localhost:8084"
    echo
    echo -e "${GREEN}Reporting:${NC}"
    echo "  kubectl port-forward service/reporting 8085:8003 -n datawarehouse"
    echo "  Then visit: http://localhost:8085"
}

# Cleanup function
cleanup() {
    print_header "Cleaning Up Deployment"
    
    print_warning "This will delete all resources in the datawarehouse namespace!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace datawarehouse --ignore-not-found=true
        print_status "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Main function
main() {
    case "$1" in
        "deploy")
            check_prerequisites
            deploy_to_railway
            wait_for_critical_services
            show_status
            show_access_info
            print_status "Deployment completed successfully!"
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "access")
            show_access_info
            ;;
        *)
            echo "Railway Kubernetes Deployment Script"
            echo
            echo "Usage: $0 {deploy|status|cleanup|access}"
            echo
            echo "Commands:"
            echo "  deploy  - Deploy the entire application to Railway"
            echo "  status  - Show current deployment status"
            echo "  cleanup - Remove all resources (with confirmation)"
            echo "  access  - Show how to access services locally"
            echo
            echo "Prerequisites:"
            echo "  - kubectl configured to connect to Railway cluster"
            echo "  - kustomize installed"
            echo "  - Docker images built and accessible by Railway"
            exit 1
            ;;
    esac
}

main "$@"
