import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Order Service!"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "order-service"}

@patch('app.main.httpx.AsyncClient')
def test_create_order_success(mock_async_client):
    # Mock the httpx client
    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance
    
    # Mock successful stock deduction
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client_instance.patch.return_value = mock_response
    
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": "test-product-id",
                "quantity": 2,
                "price_at_purchase": 29.99
            }
        ]
    }
    
    response = client.post("/orders/", json=order_data)
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == 1
    assert data["status"] == "confirmed"
    assert data["total_amount"] == 59.98
    assert len(data["items"]) == 1

def test_create_order_empty_items():
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": []
    }
    
    response = client.post("/orders/", json=order_data)
    assert response.status_code == 400
    assert "must contain at least one item" in response.json()["detail"]

@patch('app.main.httpx.AsyncClient')
def test_create_order_insufficient_stock(mock_async_client):
    # Mock the httpx client
    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance
    
    # Mock insufficient stock response
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_client_instance.patch.return_value = mock_response
    
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": "test-product-id",
                "quantity": 2,
                "price_at_purchase": 29.99
            }
        ]
    }
    
    response = client.post("/orders/", json=order_data)
    assert response.status_code == 400

def test_list_orders():
    response = client.get("/orders/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch('app.main.httpx.AsyncClient')
def test_get_order(mock_async_client):
    # Mock the httpx client
    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance
    
    # Mock successful stock deduction
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client_instance.patch.return_value = mock_response
    
    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": "test-product-id",
                "quantity": 1,
                "price_at_purchase": 29.99
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]
    
    # Get the order
    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == order_id

def test_get_order_not_found():
    response = client.get("/orders/nonexistent")
    assert response.status_code == 404

@patch('app.main.httpx.AsyncClient')
def test_update_order_status(mock_async_client):
    # Mock the httpx client
    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance
    
    # Mock successful stock deduction
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client_instance.patch.return_value = mock_response
    
    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": "test-product-id",
                "quantity": 1,
                "price_at_purchase": 29.99
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]
    
    # Update status
    response = client.patch(f"/orders/{order_id}/status?new_status=shipped")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "shipped"

@patch('app.main.httpx.AsyncClient')
def test_delete_order(mock_async_client):
    # Mock the httpx client
    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance
    
    # Mock successful stock deduction
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client_instance.patch.return_value = mock_response
    
    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": "test-product-id",
                "quantity": 1,
                "price_at_purchase": 29.99
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]
    
    # Delete the order
    response = client.delete(f"/orders/{order_id}")
    assert response.status_code == 200
    
    # Verify it's deleted
    get_response = client.get(f"/orders/{order_id}")
    assert get_response.status_code == 404

@patch('app.main.httpx.AsyncClient')
def test_get_order_items(mock_async_client):
    # Mock the httpx client
    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance
    
    # Mock successful stock deduction
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client_instance.patch.return_value = mock_response
    
    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": "test-product-id",
                "quantity": 2,
                "price_at_purchase": 29.99
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]
    
    # Get order items
    response = client.get(f"/orders/{order_id}/items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["product_id"] == "test-product-id"