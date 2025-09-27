import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Product Service!"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "product-service"}

def test_create_product():
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 29.99,
        "stock_quantity": 100
    }
    response = client.post("/products/", json=product_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"]
    assert data["stock_quantity"] == product_data["stock_quantity"]
    assert "product_id" in data

def test_list_products():
    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_product():
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 29.99,
        "stock_quantity": 100
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]
    
    # Get the product
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == product_id

def test_get_product_not_found():
    response = client.get("/products/nonexistent")
    assert response.status_code == 404

def test_update_product():
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 29.99,
        "stock_quantity": 100
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]
    
    # Update the product
    update_data = {
        "name": "Updated Product",
        "description": "Updated description",
        "price": 39.99,
        "stock_quantity": 50
    }
    response = client.put(f"/products/{product_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["price"] == update_data["price"]

def test_delete_product():
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 29.99,
        "stock_quantity": 100
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]
    
    # Delete the product
    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 200
    
    # Verify it's deleted
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404

def test_deduct_stock():
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 29.99,
        "stock_quantity": 100
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]
    
    # Deduct stock
    deduct_data = {"quantity_to_deduct": 10}
    response = client.patch(f"/products/{product_id}/deduct-stock", json=deduct_data)
    assert response.status_code == 200
    data = response.json()
    assert data["stock_quantity"] == 90

def test_deduct_stock_insufficient():
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 29.99,
        "stock_quantity": 5
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]
    
    # Try to deduct more than available
    deduct_data = {"quantity_to_deduct": 10}
    response = client.patch(f"/products/{product_id}/deduct-stock", json=deduct_data)
    assert response.status_code == 400