# Simplified Order Service Tests - API Only

import logging
from unittest.mock import AsyncMock, patch

import pytest
from app.main import PRODUCT_SERVICE_URL, app
from fastapi.testclient import TestClient

# Suppress noisy logs during tests for cleaner output
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("app.main").setLevel(logging.WARNING)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="function")
def mock_httpx_client():
    with patch("app.main.httpx.AsyncClient") as mock_async_client_cls:
        mock_client_instance = AsyncMock()
        mock_async_client_cls.return_value.__aenter__.return_value = (
            mock_client_instance
        )
        yield mock_client_instance

def test_read_root(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Order Service!"}

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "order-service"}

def test_create_order_success(client: TestClient, mock_httpx_client):
    """Test successful order creation with mocked product service."""
    # Mock successful stock deduction response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "product_id": 1,
        "name": "Test Product",
        "stock_quantity": 90,
        "price": 10.0
    }
    mock_httpx_client.patch.return_value = mock_response

    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": 1,
                "quantity": 2,
                "price_at_purchase": 10.0
            }
        ]
    }

    response = client.post("/orders/", json=order_data)
    assert response.status_code == 201
    response_data = response.json()
    
    assert response_data["user_id"] == 1
    assert response_data["status"] == "confirmed"
    assert response_data["total_amount"] == 20.0
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["product_id"] == 1
    assert response_data["items"][0]["quantity"] == 2

def test_create_order_empty_items(client: TestClient):
    """Test order creation with no items."""
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": []
    }

    response = client.post("/orders/", json=order_data)
    assert response.status_code == 400
    assert "Order must contain at least one item" in response.json()["detail"]

def test_create_order_product_service_error(client: TestClient, mock_httpx_client):
    """Test order creation when product service returns an error."""
    # Mock product service error
    mock_httpx_client.patch.side_effect = Exception("Product service unavailable")

    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": 1,
                "quantity": 2,
                "price_at_purchase": 10.0
            }
        ]
    }

    response = client.post("/orders/", json=order_data)
    assert response.status_code == 503
    assert "Product Service is currently unavailable" in response.json()["detail"]

def test_list_orders_empty(client: TestClient):
    """Test listing orders when no orders exist."""
    response = client.get("/orders/")
    assert response.status_code == 200
    assert response.json() == []

def test_list_orders_with_data(client: TestClient, mock_httpx_client):
    """Test listing orders when orders exist."""
    # Mock successful stock deduction response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "product_id": 1,
        "name": "Test Product",
        "stock_quantity": 90,
        "price": 10.0
    }
    mock_httpx_client.patch.return_value = mock_response

    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
                "price_at_purchase": 10.0
            }
        ]
    }
    client.post("/orders/", json=order_data)

    # List orders
    response = client.get("/orders/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_get_order_success(client: TestClient, mock_httpx_client):
    """Test getting a specific order by ID."""
    # Mock successful stock deduction response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "product_id": 1,
        "name": "Test Product",
        "stock_quantity": 90,
        "price": 10.0
    }
    mock_httpx_client.patch.return_value = mock_response

    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
                "price_at_purchase": 10.0
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    # Get the order
    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["order_id"] == order_id
    assert response_data["user_id"] == 1

def test_get_order_not_found(client: TestClient):
    """Test getting a non-existent order."""
    response = client.get("/orders/99999")
    assert response.status_code == 404

def test_update_order_status_success(client: TestClient, mock_httpx_client):
    """Test updating order status."""
    # Mock successful stock deduction response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "product_id": 1,
        "name": "Test Product",
        "stock_quantity": 90,
        "price": 10.0
    }
    mock_httpx_client.patch.return_value = mock_response

    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
                "price_at_purchase": 10.0
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    # Update status
    response = client.patch(f"/orders/{order_id}/status?new_status=shipped")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "shipped"

def test_delete_order_success(client: TestClient, mock_httpx_client):
    """Test deleting an order."""
    # Mock successful stock deduction response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "product_id": 1,
        "name": "Test Product",
        "stock_quantity": 90,
        "price": 10.0
    }
    mock_httpx_client.patch.return_value = mock_response

    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
                "price_at_purchase": 10.0
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    # Delete the order
    response = client.delete(f"/orders/{order_id}")
    assert response.status_code == 204

    # Verify order is no longer accessible
    get_response = client.get(f"/orders/{order_id}")
    assert get_response.status_code == 404

def test_get_order_items_success(client: TestClient, mock_httpx_client):
    """Test getting order items."""
    # Mock successful stock deduction response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "product_id": 1,
        "name": "Test Product",
        "stock_quantity": 90,
        "price": 10.0
    }
    mock_httpx_client.patch.return_value = mock_response

    # Create an order first
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St",
        "items": [
            {
                "product_id": 1,
                "quantity": 2,
                "price_at_purchase": 10.0
            }
        ]
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    # Get order items
    response = client.get(f"/orders/{order_id}/items")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["product_id"] == 1
    assert response_data[0]["quantity"] == 2