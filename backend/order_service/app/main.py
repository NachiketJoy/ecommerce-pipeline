from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
import httpx

app = FastAPI(title="Order Service", version="1.0.0")

# Simple in-memory storage
orders_db = {}

# Configuration
PRODUCT_SERVICE_URL = "http://product-service:8000"

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int
    price_at_purchase: float

class OrderCreate(BaseModel):
    user_id: int
    shipping_address: str
    items: List[OrderItemCreate]

class OrderItemResponse(BaseModel):
    order_item_id: str
    order_id: str
    product_id: str
    quantity: int
    price_at_purchase: float
    item_total: float
    created_at: datetime

class OrderResponse(BaseModel):
    order_id: str
    user_id: int
    shipping_address: str
    status: str
    total_amount: float
    items: List[OrderItemResponse]
    order_date: datetime

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Order Service!"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "order-service"}

@app.post("/orders/", response_model=OrderResponse)
async def create_order(order: OrderCreate):
    if not order.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")
    
    order_id = str(uuid.uuid4())
    total_amount = 0
    order_items = []
    
    # Process each item
    async with httpx.AsyncClient() as client:
        for item in order.items:
            # Deduct stock from product service
            try:
                deduct_response = await client.patch(
                    f"{PRODUCT_SERVICE_URL}/products/{item.product_id}/deduct-stock",
                    json={"quantity_to_deduct": item.quantity},
                    timeout=5.0
                )
                deduct_response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    raise HTTPException(status_code=400, detail=f"Insufficient stock for product {item.product_id}")
                elif e.response.status_code == 404:
                    raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
                else:
                    raise HTTPException(status_code=503, detail="Product service unavailable")
            except httpx.RequestError:
                raise HTTPException(status_code=503, detail="Product service unavailable")
            
            # Create order item
            item_id = str(uuid.uuid4())
            item_total = item.quantity * item.price_at_purchase
            total_amount += item_total
            
            order_item = {
                "order_item_id": item_id,
                "order_id": order_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase,
                "item_total": item_total,
                "created_at": datetime.now()
            }
            order_items.append(order_item)
    
    # Create order
    order_data = {
        "order_id": order_id,
        "user_id": order.user_id,
        "shipping_address": order.shipping_address,
        "status": "confirmed",
        "total_amount": total_amount,
        "items": order_items,
        "order_date": datetime.now()
    }
    
    orders_db[order_id] = order_data
    return OrderResponse(**order_data)

@app.get("/orders/", response_model=List[OrderResponse])
async def list_orders():
    return [OrderResponse(**order) for order in orders_db.values()]

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(**orders_db[order_id])

@app.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(order_id: str, new_status: str):
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    
    orders_db[order_id]["status"] = new_status
    return OrderResponse(**orders_db[order_id])

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    del orders_db[order_id]
    return {"message": "Order deleted successfully"}

@app.get("/orders/{order_id}/items", response_model=List[OrderItemResponse])
async def get_order_items(order_id: str):
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    return [OrderItemResponse(**item) for item in orders_db[order_id]["items"]]