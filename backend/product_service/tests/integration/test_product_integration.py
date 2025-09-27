# Simplified Product Service Integration Tests - API Only

import logging
import os
import time
from unittest.mock import patch

import pytest
import requests
from fastapi.testclient import TestClient

from app.main import app

# Suppress noisy logs during integration tests
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("app.main").setLevel(logging.WARNING)


@pytest.fixture(scope="module")
def client():
    """Create a test client for integration tests."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module", autouse=True)
def setup_integration_environment():
    """Set up environment variables for integration tests."""
    os.environ["AZURE_STORAGE_ACCOUNT_NAME"] = "testaccount"
    os.environ["AZURE_STORAGE_ACCOUNT_KEY"] = "testkey"
    os.environ["AZURE_STORAGE_CONTAINER_NAME"] = "test-images"
    os.environ["AZURE_SAS_TOKEN_EXPIRY_HOURS"] = "1"
    yield
    # Clean up environment variables after tests
    for key in ["AZURE_STORAGE_ACCOUNT_NAME", "AZURE_STORAGE_ACCOUNT_KEY", 
                "AZURE_STORAGE_CONTAINER_NAME", "AZURE_SAS_TOKEN_EXPIRY_HOURS"]:
        if key in os.environ:
            del os.environ[key]


class TestProductServiceIntegration:
    """Integration tests for Product Service."""

    def test_create_and_retrieve_product_flow(self, client):
        """Test the complete flow of creating and retrieving a product."""
        # Create a product
        product_data = {
            "name": "Integration Test Product",
            "description": "A product for integration testing",
            "price": 29.99,
            "stock_quantity": 50,
            "image_url": "http://example.com/test.jpg"
        }
        
        create_response = client.post("/products/", json=product_data)
        assert create_response.status_code == 201
        
        created_product = create_response.json()
        product_id = created_product["product_id"]
        
        # Retrieve the product
        get_response = client.get(f"/products/{product_id}")
        assert get_response.status_code == 200
        
        retrieved_product = get_response.json()
        assert retrieved_product["name"] == product_data["name"]
        assert retrieved_product["price"] == product_data["price"]
        assert retrieved_product["stock_quantity"] == product_data["stock_quantity"]

    def test_product_lifecycle_flow(self, client):
        """Test the complete lifecycle of a product: create, update, delete."""
        # Create a product
        product_data = {
            "name": "Lifecycle Test Product",
            "description": "A product for lifecycle testing",
            "price": 19.99,
            "stock_quantity": 25
        }
        
        create_response = client.post("/products/", json=product_data)
        assert create_response.status_code == 201
        product_id = create_response.json()["product_id"]
        
        # Update the product
        update_data = {
            "name": "Updated Lifecycle Test Product",
            "price": 24.99,
            "stock_quantity": 30
        }
        
        update_response = client.put(f"/products/{product_id}", json=update_data)
        assert update_response.status_code == 200
        
        updated_product = update_response.json()
        assert updated_product["name"] == update_data["name"]
        assert updated_product["price"] == update_data["price"]
        assert updated_product["stock_quantity"] == update_data["stock_quantity"]
        
        # Delete the product
        delete_response = client.delete(f"/products/{product_id}")
        assert delete_response.status_code == 204
        
        # Verify product is deleted
        get_response = client.get(f"/products/{product_id}")
        assert get_response.status_code == 404

    def test_stock_deduction_flow(self, client):
        """Test the stock deduction functionality."""
        # Create a product with stock
        product_data = {
            "name": "Stock Test Product",
            "description": "A product for stock testing",
            "price": 15.99,
            "stock_quantity": 100
        }
        
        create_response = client.post("/products/", json=product_data)
        assert create_response.status_code == 201
        product_id = create_response.json()["product_id"]
        
        # Deduct stock
        deduct_data = {"quantity_to_deduct": 10}
        deduct_response = client.patch(f"/products/{product_id}/deduct-stock", json=deduct_data)
        assert deduct_response.status_code == 200
        
        updated_product = deduct_response.json()
        assert updated_product["stock_quantity"] == 90
        
        # Try to deduct more stock than available
        deduct_data = {"quantity_to_deduct": 100}
        deduct_response = client.patch(f"/products/{product_id}/deduct-stock", json=deduct_data)
        assert deduct_response.status_code == 400

    def test_product_search_functionality(self, client):
        """Test the product search functionality."""
        # Create multiple products
        products = [
            {
                "name": "Search Test Product 1",
                "description": "A product with unique description",
                "price": 10.99,
                "stock_quantity": 20
            },
            {
                "name": "Search Test Product 2",
                "description": "Another product with different description",
                "price": 20.99,
                "stock_quantity": 30
            },
            {
                "name": "Unique Product Name",
                "description": "A product with unique name",
                "price": 30.99,
                "stock_quantity": 40
            }
        ]
        
        created_products = []
        for product_data in products:
            response = client.post("/products/", json=product_data)
            assert response.status_code == 201
            created_products.append(response.json())
        
        # Search by name
        search_response = client.get("/products/?search=Search")
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results) == 2
        
        # Search by description
        search_response = client.get("/products/?search=unique")
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results) == 2

    def test_pagination_functionality(self, client):
        """Test the pagination functionality."""
        # Create multiple products
        for i in range(15):
            product_data = {
                "name": f"Pagination Test Product {i}",
                "description": f"Product {i} for pagination testing",
                "price": 10.99 + i,
                "stock_quantity": 20 + i
            }
            response = client.post("/products/", json=product_data)
            assert response.status_code == 201
        
        # Test pagination
        page1_response = client.get("/products/?skip=0&limit=10")
        assert page1_response.status_code == 200
        page1_results = page1_response.json()
        assert len(page1_results) == 10
        
        page2_response = client.get("/products/?skip=10&limit=10")
        assert page2_response.status_code == 200
        page2_results = page2_response.json()
        assert len(page2_results) == 5  # Remaining products

    @patch('app.main.blob_service_client')
    def test_image_upload_integration(self, mock_blob_client, client):
        """Test image upload functionality with mocked Azure storage."""
        # Create a product first
        product_data = {
            "name": "Image Upload Test Product",
            "description": "A product for image upload testing",
            "price": 25.99,
            "stock_quantity": 15
        }
        
        create_response = client.post("/products/", json=product_data)
        assert create_response.status_code == 201
        product_id = create_response.json()["product_id"]
        
        # Mock the Azure blob client
        mock_blob_client.get_blob_client.return_value.upload_blob.return_value = None
        mock_blob_client.get_blob_client.return_value.url = "https://test.blob.core.windows.net/test/test.jpg"
        
        # Create a test image file
        test_image_content = b"fake image content"
        
        # Upload image
        files = {"file": ("test.jpg", test_image_content, "image/jpeg")}
        upload_response = client.post(f"/products/{product_id}/upload-image", files=files)
        assert upload_response.status_code == 200
        
        updated_product = upload_response.json()
        assert "image_url" in updated_product
        assert updated_product["image_url"] is not None

    def test_error_handling_integration(self, client):
        """Test error handling in various scenarios."""
        # Test creating product with invalid data
        invalid_product_data = {
            "name": "",  # Empty name should fail validation
            "price": -10,  # Negative price should fail validation
            "stock_quantity": -5  # Negative stock should fail validation
        }
        
        response = client.post("/products/", json=invalid_product_data)
        assert response.status_code == 422  # Validation error
        
        # Test retrieving non-existent product
        response = client.get("/products/99999")
        assert response.status_code == 404
        
        # Test updating non-existent product
        update_data = {"name": "Updated Name"}
        response = client.put("/products/99999", json=update_data)
        assert response.status_code == 404
        
        # Test deleting non-existent product
        response = client.delete("/products/99999")
        assert response.status_code == 404

    def test_concurrent_operations(self, client):
        """Test concurrent operations on the same product."""
        import threading
        import time
        
        # Create a product
        product_data = {
            "name": "Concurrent Test Product",
            "description": "A product for concurrent testing",
            "price": 35.99,
            "stock_quantity": 100
        }
        
        create_response = client.post("/products/", json=product_data)
        assert create_response.status_code == 201
        product_id = create_response.json()["product_id"]
        
        # Function to deduct stock
        def deduct_stock(quantity):
            deduct_data = {"quantity_to_deduct": quantity}
            response = client.patch(f"/products/{product_id}/deduct-stock", json=deduct_data)
            return response.status_code == 200
        
        # Run concurrent stock deductions
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(target=lambda: results.append(deduct_stock(10)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all deductions were successful
        assert all(results)
        
        # Verify final stock quantity
        get_response = client.get(f"/products/{product_id}")
        assert get_response.status_code == 200
        final_product = get_response.json()
        assert final_product["stock_quantity"] == 50  # 100 - (5 * 10)
