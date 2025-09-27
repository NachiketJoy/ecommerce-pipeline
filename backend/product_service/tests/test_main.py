# Simplified Product Service Tests - API Only

import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from app.main import app
from fastapi.testclient import TestClient

# Suppress noisy logs during tests for cleaner output
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("app.main").setLevel(logging.WARNING)

@pytest.fixture(scope="module")
def client():
    os.environ["AZURE_STORAGE_ACCOUNT_NAME"] = "testaccount"
    os.environ["AZURE_STORAGE_ACCOUNT_KEY"] = "testkey"
    os.environ["AZURE_STORAGE_CONTAINER_NAME"] = "test-images"
    os.environ["AZURE_SAS_TOKEN_EXPIRY_HOURS"] = "1"  # Short expiry for tests

    with TestClient(app) as test_client:
        yield test_client

    # Clean up environment variables after tests
    del os.environ["AZURE_STORAGE_ACCOUNT_NAME"]
    del os.environ["AZURE_STORAGE_ACCOUNT_KEY"]
    del os.environ["AZURE_STORAGE_CONTAINER_NAME"]
    del os.environ["AZURE_SAS_TOKEN_EXPIRY_HOURS"]

@pytest.fixture(scope="function", autouse=True)
def mock_azure_blob_storage():
    """
    Mocks the Azure Blob Storage client to prevent actual uploads during tests.
    """
    with patch("app.main.BlobServiceClient") as mock_blob_service_client:
        mock_instance = MagicMock()
        mock_blob_service_client.return_value = mock_instance

        # Mock the get_container_client method
        mock_container_client = MagicMock()
        mock_instance.get_container_client.return_value = mock_container_client

        # Mock the create_container method
        mock_container_client.create_container.return_value = None

        # Mock the get_blob_client method
        mock_blob_client = MagicMock()
        mock_instance.get_blob_client.return_value = mock_blob_client

        # Mock the upload_blob method
        mock_blob_client.upload_blob.return_value = None

        # Mock the blob_client.url attribute
        mock_blob_client.url = (
            "https://testaccount.blob.core.windows.net/test-images/mock_blob.jpg"
        )

        # Mock generate_blob_sas
        with patch("app.main.generate_blob_sas") as mock_generate_blob_sas:
            mock_generate_blob_sas.return_value = "sv=2021-08-01&st=2024-01-01T00%3A00%3A00Z&se=2024-01-01T01%3A00%3A00Z&sr=b&sp=r&sig=mock_sas_token"
            yield mock_blob_service_client

@pytest.fixture(scope="function", autouse=True)
def clear_products_db():
    """
    Clears the products database before each test to ensure test isolation.
    """
    from app.main import products_db
    products_db.clear()
    yield
    products_db.clear()

# --- Product Service Tests ---

def test_read_root(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Product Service!"}

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "product-service"}

def test_create_product_success(client: TestClient):
    """
    Tests successful creation of a product via POST /products/.
    Verifies status code, response data, and in-memory storage.
    """
    test_data = {
        "name": "New Test Product",
        "description": "A brand new product for testing",
        "price": 12.34,
        "stock_quantity": 100,
        "image_url": "http://example.com/test_image.jpg",
    }
    response = client.post("/products/", json=test_data)

    assert response.status_code == 201
    response_data = response.json()

    # Assert response fields match input and generated fields exist
    assert response_data["name"] == test_data["name"]
    assert response_data["description"] == test_data["description"]
    assert float(response_data["price"]) == test_data["price"]
    assert response_data["stock_quantity"] == test_data["stock_quantity"]
    assert response_data["image_url"] == test_data["image_url"]
    assert "product_id" in response_data
    assert isinstance(response_data["product_id"], int)
    assert "created_at" in response_data

def test_list_products_empty(client: TestClient):
    """
    Tests listing products when no products exist, expecting an empty list.
    """
    response = client.get("/products/")
    assert response.status_code == 200
    assert response.json() == []

def test_list_products_with_data(client: TestClient):
    """
    Tests listing products when products exist, verifying the list structure.
    """
    # Create a product via API
    product_data = {
        "name": "List Product Example",
        "description": "For list test",
        "price": 5.00,
        "stock_quantity": 10,
        "image_url": "http://example.com/list_test.png",
    }
    client.post("/products/", json=product_data)

    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_get_product_success(client: TestClient):
    """Test getting a specific product by ID."""
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "Test description",
        "price": 10.0,
        "stock_quantity": 5,
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]

    # Get the product
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["product_id"] == product_id
    assert response_data["name"] == product_data["name"]

def test_get_product_not_found(client: TestClient):
    """Test getting a non-existent product."""
    response = client.get("/products/99999")
    assert response.status_code == 404

def test_update_product_success(client: TestClient):
    """Test updating a product."""
    # Create a product first
    product_data = {
        "name": "Original Product",
        "description": "Original description",
        "price": 10.0,
        "stock_quantity": 5,
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]

    # Update the product
    update_data = {
        "name": "Updated Product",
        "price": 15.0,
    }
    response = client.put(f"/products/{product_id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["name"] == "Updated Product"
    assert response_data["price"] == 15.0
    assert response_data["description"] == "Original description"  # Should remain unchanged

def test_delete_product_success(client: TestClient):
    """
    Tests successful deletion of a product.
    """
    # Create a product specifically for deletion
    create_resp = client.post(
        "/products/",
        json={
            "name": "Product to Delete",
            "description": "Will be deleted",
            "price": 10.0,
            "stock_quantity": 5,
            "image_url": "http://example.com/to_delete.jpeg",
        },
    )
    product_id = create_resp.json()["product_id"]

    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 204  # No content on successful delete

    # Verify product is no longer accessible
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404

def test_deduct_stock_success(client: TestClient):
    """Test successful stock deduction."""
    # Create a product with stock
    product_data = {
        "name": "Stock Test Product",
        "description": "For stock testing",
        "price": 10.0,
        "stock_quantity": 100,
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]

    # Deduct stock
    deduct_data = {"quantity_to_deduct": 10}
    response = client.patch(f"/products/{product_id}/deduct-stock", json=deduct_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["stock_quantity"] == 90

def test_deduct_stock_insufficient(client: TestClient):
    """Test stock deduction with insufficient stock."""
    # Create a product with limited stock
    product_data = {
        "name": "Limited Stock Product",
        "description": "For stock testing",
        "price": 10.0,
        "stock_quantity": 5,
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]

    # Try to deduct more than available
    deduct_data = {"quantity_to_deduct": 10}
    response = client.patch(f"/products/{product_id}/deduct-stock", json=deduct_data)
    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]