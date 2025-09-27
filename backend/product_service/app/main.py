from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

app = FastAPI(title="Product Service", version="1.0.0")

# Simple in-memory storage
products_db = {}

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock_quantity: int
    image_url: Optional[str] = None

class ProductResponse(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    stock_quantity: int
    image_url: Optional[str] = None
    created_at: datetime

class StockDeductRequest(BaseModel):
    quantity_to_deduct: int

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Product Service!"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "product-service"}

@app.post("/products/", response_model=ProductResponse)
async def create_product(product: ProductCreate):
    product_id = str(uuid.uuid4())
    product_data = {
        "product_id": product_id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock_quantity": product.stock_quantity,
        "image_url": product.image_url,
        "created_at": datetime.now()
    }
    products_db[product_id] = product_data
    return ProductResponse(**product_data)

@app.get("/products/", response_model=List[ProductResponse])
async def list_products():
    return [ProductResponse(**product) for product in products_db.values()]

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(**products_db[product_id])

@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, product: ProductCreate):
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    products_db[product_id].update({
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock_quantity": product.stock_quantity,
        "image_url": product.image_url
    })
    return ProductResponse(**products_db[product_id])

@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    del products_db[product_id]
    return {"message": "Product deleted successfully"}

@app.patch("/products/{product_id}/deduct-stock", response_model=ProductResponse)
async def deduct_stock(product_id: str, request: StockDeductRequest):
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = products_db[product_id]
    if product["stock_quantity"] < request.quantity_to_deduct:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient stock. Available: {product['stock_quantity']}, Requested: {request.quantity_to_deduct}"
        )
    
    product["stock_quantity"] -= request.quantity_to_deduct
    return ProductResponse(**product)