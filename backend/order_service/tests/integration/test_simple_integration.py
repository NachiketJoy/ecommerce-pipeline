# Simple Integration Test for Order Service

import os
import requests
import pytest

# Integration test configuration
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8001")

def test_order_service_health():
    """Test that the order service is healthy and responding."""
    response = requests.get(f"{ORDER_SERVICE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "order-service"

def test_order_service_root():
    """Test that the order service root endpoint is responding."""
    response = requests.get(f"{ORDER_SERVICE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_list_orders():
    """Test listing orders."""
    response = requests.get(f"{ORDER_SERVICE_URL}/orders/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
