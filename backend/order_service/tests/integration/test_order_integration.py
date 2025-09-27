# week08/backend/order_service/tests/integration/test_order_integration.py

import logging
import os
import time
from unittest.mock import AsyncMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from app.main import app

# Suppress noisy logs during integration tests
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("app.main").setLevel(logging.WARNING)


@pytest.fixture(scope="module")
def client():
    """Create a test client for integration tests."""
    with TestClient(app) as test_client:
        yield test_client


class TestOrderServiceIntegration:
    """Integration tests for Order Service."""

    @patch('app.main.httpx.AsyncClient')
    def test_create_order_with_successful_stock_deduction(self, mock_async_client, client):
        """Test creating an order with successful stock deduction from product service."""
        # Mock the httpx client for product service calls
        mock_client_instance = AsyncMock()
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock successful stock deduction response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "product_id": 1,
            "name": "Test Product",
            "stock_quantity": 90,
            "price": 29.99
        }
        mock_client_instance.patch.return_value = mock_response
        
        # Create an order
        order_data = {
            "user_id": 1,
            "shipping_address": "123 Test Street, Test City",
            "items": [
                {
                    "product_id": 1,
                    "quantity": 2,
                    "price_at_purchase": 29.99
                }
            ]
        }
        
        response = client.post("/orders/", json=order_data)
        assert response.status_code == 201
        
        order = response.json()
        assert order["user_id"] == order_data["user_id"]
        assert order["shipping_address"] == order_data["shipping_address"]
        assert order["status"] == "confirmed"
        assert len(order["items"]) == 1
        assert order["items"][0]["product_id"] == 1
        assert order["items"][0]["quantity"] == 2

    @patch('app.main.httpx.AsyncClient')
    def test_create_order_with_insufficient_stock(self, mock_async_client, client):
        """Test creating an order when product service reports insufficient stock."""
        # Mock the httpx client for product service calls
        mock_client_instance = AsyncMock()
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock insufficient stock response
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "detail": "Insufficient stock for product 'Test Product'. Only 5 available."
        }
        mock_client_instance.patch.return_value = mock_response
        
        # Create an order with quantity higher than available stock
        order_data = {
            "user_id": 1,
            "shipping_address": "123 Test Street, Test City",
            "items": [
                {
                    "product_id": 1,
                    "quantity": 10,  # More than available stock
                    "price_at_purchase": 29.99
                }
            ]
        }
        
        response = client.post("/orders/", json=order_data)
        assert response.status_code == 400
        assert "insufficient stock" in response.json()["detail"].lower()

    @patch('app.main.httpx.AsyncClient')
    def test_create_order_with_product_not_found(self, mock_async_client, client):
        """Test creating an order when product service reports product not found."""
        # Mock the httpx client for product service calls
        mock_client_instance = AsyncMock()
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock product not found response
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "detail": "Product not found"
        }
        mock_client_instance.patch.return_value = mock_response
        
        # Create an order with non-existent product
        order_data = {
            "user_id": 1,
            "shipping_address": "123 Test Street, Test City",
            "items": [
                {
                    "product_id": 999,  # Non-existent product
                    "quantity": 1,
                    "price_at_purchase": 29.99
                }
            ]
        }
        
        response = client.post("/orders/", json=order_data)
        assert response.status_code == 400
        assert "product not found" in response.json()["detail"].lower()

    @patch('app.main.httpx.AsyncClient')
    def test_create_order_with_product_service_unavailable(self, mock_async_client, client):
        """Test creating an order when product service is unavailable."""
        # Mock the httpx client for product service calls
        mock_client_instance = AsyncMock()
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock network error
        import httpx
        mock_client_instance.patch.side_effect = httpx.RequestError("Connection failed")
        
        # Create an order
        order_data = {
            "user_id": 1,
            "shipping_address": "123 Test Street, Test City",
            "items": [
                {
                    "product_id": 1,
                    "quantity": 1,
                    "price_at_purchase": 29.99
                }
            ]
        }
        
        response = client.post("/orders/", json=order_data)
        assert response.status_code == 503
        assert "service is currently unavailable" in response.json()["detail"].lower()

    def test_order_lifecycle_flow(self, client):
        """Test the complete lifecycle of an order: create, retrieve, update status, delete."""
        # Create an order (with mocked product service)
        with patch('app.main.httpx.AsyncClient') as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock successful stock deduction
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "product_id": 1,
                "name": "Test Product",
                "stock_quantity": 90,
                "price": 29.99
            }
            mock_client_instance.patch.return_value = mock_response
            
            order_data = {
                "user_id": 1,
                "shipping_address": "123 Test Street, Test City",
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 1,
                        "price_at_purchase": 29.99
                    }
                ]
            }
            
            create_response = client.post("/orders/", json=order_data)
            assert create_response.status_code == 201
            order_id = create_response.json()["order_id"]
        
        # Retrieve the order
        get_response = client.get(f"/orders/{order_id}")
        assert get_response.status_code == 200
        retrieved_order = get_response.json()
        assert retrieved_order["order_id"] == order_id
        assert retrieved_order["status"] == "confirmed"
        
        # Update order status
        update_response = client.patch(f"/orders/{order_id}/status?new_status=shipped")
        assert update_response.status_code == 200
        updated_order = update_response.json()
        assert updated_order["status"] == "shipped"
        
        # Delete the order
        delete_response = client.delete(f"/orders/{order_id}")
        assert delete_response.status_code == 204
        
        # Verify order is deleted
        get_response = client.get(f"/orders/{order_id}")
        assert get_response.status_code == 404

    def test_list_orders_with_filters(self, client):
        """Test listing orders with various filters."""
        # Create multiple orders with different users and statuses
        with patch('app.main.httpx.AsyncClient') as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock successful stock deduction
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "product_id": 1,
                "name": "Test Product",
                "stock_quantity": 90,
                "price": 29.99
            }
            mock_client_instance.patch.return_value = mock_response
            
            # Create orders for different users
            for user_id in [1, 2, 1]:  # Two orders for user 1, one for user 2
                order_data = {
                    "user_id": user_id,
                    "shipping_address": f"123 Test Street, User {user_id}",
                    "items": [
                        {
                            "product_id": 1,
                            "quantity": 1,
                            "price_at_purchase": 29.99
                        }
                    ]
                }
                response = client.post("/orders/", json=order_data)
                assert response.status_code == 201
        
        # Test listing all orders
        all_orders_response = client.get("/orders/")
        assert all_orders_response.status_code == 200
        all_orders = all_orders_response.json()
        assert len(all_orders) >= 3
        
        # Test filtering by user_id
        user1_orders_response = client.get("/orders/?user_id=1")
        assert user1_orders_response.status_code == 200
        user1_orders = user1_orders_response.json()
        assert len(user1_orders) >= 2
        assert all(order["user_id"] == 1 for order in user1_orders)
        
        # Test filtering by status
        confirmed_orders_response = client.get("/orders/?status=confirmed")
        assert confirmed_orders_response.status_code == 200
        confirmed_orders = confirmed_orders_response.json()
        assert all(order["status"] == "confirmed" for order in confirmed_orders)

    def test_order_items_retrieval(self, client):
        """Test retrieving order items."""
        # Create an order
        with patch('app.main.httpx.AsyncClient') as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock successful stock deduction
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "product_id": 1,
                "name": "Test Product",
                "stock_quantity": 90,
                "price": 29.99
            }
            mock_client_instance.patch.return_value = mock_response
            
            order_data = {
                "user_id": 1,
                "shipping_address": "123 Test Street, Test City",
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 2,
                        "price_at_purchase": 29.99
                    },
                    {
                        "product_id": 2,
                        "quantity": 1,
                        "price_at_purchase": 19.99
                    }
                ]
            }
            
            create_response = client.post("/orders/", json=order_data)
            assert create_response.status_code == 201
            order_id = create_response.json()["order_id"]
        
        # Retrieve order items
        items_response = client.get(f"/orders/{order_id}/items")
        assert items_response.status_code == 200
        items = items_response.json()
        assert len(items) == 2
        assert items[0]["product_id"] == 1
        assert items[0]["quantity"] == 2
        assert items[1]["product_id"] == 2
        assert items[1]["quantity"] == 1

    def test_error_handling_integration(self, client):
        """Test error handling in various scenarios."""
        # Test creating order with empty items
        order_data = {
            "user_id": 1,
            "shipping_address": "123 Test Street, Test City",
            "items": []
        }
        
        response = client.post("/orders/", json=order_data)
        assert response.status_code == 400
        assert "must contain at least one item" in response.json()["detail"]
        
        # Test retrieving non-existent order
        response = client.get("/orders/99999")
        assert response.status_code == 404
        
        # Test updating status of non-existent order
        response = client.patch("/orders/99999/status?new_status=shipped")
        assert response.status_code == 404
        
        # Test deleting non-existent order
        response = client.delete("/orders/99999")
        assert response.status_code == 404
        
        # Test retrieving items for non-existent order
        response = client.get("/orders/99999/items")
        assert response.status_code == 404

    def test_pagination_functionality(self, client):
        """Test pagination functionality for orders."""
        # Create multiple orders
        with patch('app.main.httpx.AsyncClient') as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock successful stock deduction
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "product_id": 1,
                "name": "Test Product",
                "stock_quantity": 90,
                "price": 29.99
            }
            mock_client_instance.patch.return_value = mock_response
            
            for i in range(15):
                order_data = {
                    "user_id": i + 1,
                    "shipping_address": f"123 Test Street, User {i + 1}",
                    "items": [
                        {
                            "product_id": 1,
                            "quantity": 1,
                            "price_at_purchase": 29.99
                        }
                    ]
                }
                response = client.post("/orders/", json=order_data)
                assert response.status_code == 201
        
        # Test pagination
        page1_response = client.get("/orders/?skip=0&limit=10")
        assert page1_response.status_code == 200
        page1_results = page1_response.json()
        assert len(page1_results) == 10
        
        page2_response = client.get("/orders/?skip=10&limit=10")
        assert page2_response.status_code == 200
        page2_results = page2_response.json()
        assert len(page2_results) == 5  # Remaining orders

    def test_order_total_calculation(self, client):
        """Test that order total is calculated correctly."""
        with patch('app.main.httpx.AsyncClient') as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock successful stock deduction
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "product_id": 1,
                "name": "Test Product",
                "stock_quantity": 90,
                "price": 29.99
            }
            mock_client_instance.patch.return_value = mock_response
            
            # Create order with multiple items
            order_data = {
                "user_id": 1,
                "shipping_address": "123 Test Street, Test City",
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 2,
                        "price_at_purchase": 29.99
                    },
                    {
                        "product_id": 2,
                        "quantity": 1,
                        "price_at_purchase": 19.99
                    }
                ]
            }
            
            response = client.post("/orders/", json=order_data)
            assert response.status_code == 201
            
            order = response.json()
            expected_total = (2 * 29.99) + (1 * 19.99)  # 79.97
            assert float(order["total_amount"]) == expected_total
