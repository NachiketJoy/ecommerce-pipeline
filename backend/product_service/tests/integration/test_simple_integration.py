# Simple Integration Test for Product Service

import os
import requests
import pytest

# Integration test configuration
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")

def test_product_service_health():
    """Test that the product service is healthy and responding."""
    response = requests.get(f"{PRODUCT_SERVICE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "product-service"

def test_product_service_root():
    """Test that the product service root endpoint is responding."""
    response = requests.get(f"{PRODUCT_SERVICE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_create_and_get_product():
    """Test creating and retrieving a product."""
    # Create a product
    product_data = {
        "name": "Integration Test Product",
        "description": "A product for integration testing",
        "price": 29.99,
        "stock_quantity": 50,
        "image_url": "http://example.com/test.jpg"
    }
    
    create_response = requests.post(f"{PRODUCT_SERVICE_URL}/products/", json=product_data)
    assert create_response.status_code == 201
    
    created_product = create_response.json()
    product_id = created_product["product_id"]
    
    # Retrieve the product
    get_response = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
    assert get_response.status_code == 200
    
    retrieved_product = get_response.json()
    assert retrieved_product["name"] == product_data["name"]
    assert retrieved_product["price"] == product_data["price"]
    assert retrieved_product["stock_quantity"] == product_data["stock_quantity"]
