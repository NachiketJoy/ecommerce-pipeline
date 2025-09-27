# Simplified Order Service - API Only

import logging
import os
import sys
from decimal import Decimal
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .schemas import OrderCreate, OrderItemResponse, OrderResponse, OrderUpdate

# --- Standard Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Suppress noisy logs from third-party libraries for cleaner output
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")
logger.info(
    f"Order Service: Configured to communicate with Product Service at: {PRODUCT_SERVICE_URL}"
)

# In-memory storage for orders
orders_db = {}
order_items_db = {}
next_order_id = 1
next_order_item_id = 1

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Order Service API",
    description="Manages orders for mini-ecommerce app, with synchronous stock deduction.",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root Endpoint ---
@app.get("/", status_code=status.HTTP_200_OK, summary="Root endpoint")
async def read_root():
    return {"message": "Welcome to the Order Service!"}

# --- Health Check Endpoint ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "service": "order-service"}

@app.post(
    "/orders/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
)
async def create_order(order: OrderCreate):
    if not order.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item.",
        )

    # List to store successfully deducted items in case of partial failures
    successfully_deducted_items = []
    logger.info(f"Order Service: Creating new order for user_id: {order.user_id}")

    # Use an httpx client for synchronous calls to the Product Service
    async with httpx.AsyncClient() as client:
        for item in order.items:
            product_id = item.product_id
            quantity = item.quantity

            deduct_stock_url = (
                f"{PRODUCT_SERVICE_URL}/products/{product_id}/deduct-stock"
            )
            logger.info(
                f"Order Service: Attempting to deduct stock for product {product_id} (qty: {quantity}) via Product Service at {deduct_stock_url}"
            )
            
            try:
                # Synchronous call to Product Service to deduct stock
                response = await client.patch(
                    deduct_stock_url,
                    json={"quantity_to_deduct": quantity},
                    timeout=5,  # Set a timeout for the external API call
                )
                response.raise_for_status()  # Raise an exception for 4xx/5xx responses

                logger.info(
                    f"Order Service: Stock deduction successful for product {product_id}."
                )
                successfully_deducted_items.append(item)

            except httpx.HTTPStatusError as e:
                # Handle specific HTTP errors from Product Service
                error_detail = "Unknown error during stock deduction."
                if e.response.status_code == status.HTTP_404_NOT_FOUND:
                    error_detail = f"Product {product_id} not found."
                elif e.response.status_code == status.HTTP_400_BAD_REQUEST:
                    response_json = e.response.json()
                    error_detail = response_json.get(
                        "detail", "Insufficient stock or invalid request."
                    )

                logger.error(
                    f"Order Service: Stock deduction failed for product {product_id}: {error_detail}. Status: {e.response.status_code}"
                )
                # Rollback any previously successful deductions in case of failure
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,  # Or appropriate status
                    detail=f"Failed to deduct stock for product {product_id}: {error_detail}",
                )
            except httpx.RequestError as e:
                # Handle network errors (e.g., Product Service is down)
                logger.critical(
                    f"Order Service: Network error communicating with Product Service for product {product_id}: {e}"
                )
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Product Service is currently unavailable. Please try again later. Error: {e}",
                )
            except Exception as e:
                # Catch any other unexpected errors during deduction
                logger.error(
                    f"Order Service: An unexpected error occurred during stock deduction for product {product_id}: {e}",
                    exc_info=True,
                )
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred during order creation: {e}",
                )

    # If all stock deductions are successful, proceed with order creation
    logger.info(
        "Order Service: All product stock deductions successful. Proceeding to create order."
    )

    global next_order_id, next_order_item_id
    from datetime import datetime
    
    total_amount = sum(
        Decimal(str(item.quantity)) * Decimal(str(item.price_at_purchase))
        for item in order.items
    )

    # Create order
    order_data = {
        "order_id": next_order_id,
        "user_id": order.user_id,
        "order_date": datetime.now(),
        "status": "confirmed",  # Set status to confirmed here
        "total_amount": float(total_amount),
        "shipping_address": order.shipping_address,
        "created_at": datetime.now(),
    }
    
    orders_db[next_order_id] = order_data

    # Create order items
    order_items = []
    for item in order.items:
        item_total = Decimal(str(item.quantity)) * Decimal(str(item.price_at_purchase))
        
        order_item_data = {
            "order_item_id": next_order_item_id,
            "order_id": next_order_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price_at_purchase": item.price_at_purchase,
            "item_total": float(item_total),
            "created_at": datetime.now(),
        }
        
        order_items_db[next_order_item_id] = order_item_data
        order_items.append(OrderItemResponse(**order_item_data))
        next_order_item_id += 1

    order_data["items"] = order_items
    next_order_id += 1

    logger.info(
        f"Order Service: Order {order_data['order_id']} created and confirmed successfully for user {order_data['user_id']}."
    )
    return OrderResponse(**order_data)

async def _rollback_stock_deductions(client: httpx.AsyncClient, items: List):
    if not items:
        return

    logger.warning(
        "Order Service: Attempting to rollback stock deductions due to order creation failure."
    )
    for item in items:
        product_id = item.product_id
        quantity = item.quantity

        logger.warning(
            f"Order Service: Cannot automatically rollback stock for product {product_id} quantity {quantity}. Manual stock adjustment may be required in Product Service."
        )

@app.get(
    "/orders/",
    response_model=List[OrderResponse],
    summary="Retrieve a list of all orders",
)
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user_id: Optional[int] = Query(None, ge=1, description="Filter orders by user ID."),
    status: Optional[str] = Query(
        None,
        max_length=50,
        description="Filter orders by status (e.g., pending, shipped).",
    ),
):
    logger.info(
        f"Order Service: Listing orders (skip={skip}, limit={limit}, user_id={user_id}, status='{status}')"
    )
    
    orders = list(orders_db.values())
    
    # Apply filters
    if user_id:
        orders = [o for o in orders if o["user_id"] == user_id]
    if status:
        orders = [o for o in orders if o["status"] == status]
    
    # Apply pagination
    orders = orders[skip:skip + limit]
    
    # Add items to each order
    for order in orders:
        order_items = [
            OrderItemResponse(**item) 
            for item in order_items_db.values() 
            if item["order_id"] == order["order_id"]
        ]
        order["items"] = order_items
    
    logger.info(f"Order Service: Retrieved {len(orders)} orders.")
    return [OrderResponse(**order) for order in orders]

@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Retrieve a single order by ID",
)
def get_order(order_id: int):
    logger.info(f"Order Service: Fetching order with ID: {order_id}")
    
    if order_id not in orders_db:
        logger.warning(f"Order Service: Order with ID {order_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    order = orders_db[order_id]
    
    # Add items to the order
    order_items = [
        OrderItemResponse(**item) 
        for item in order_items_db.values() 
        if item["order_id"] == order_id
    ]
    order["items"] = order_items

    logger.info(
        f"Order Service: Retrieved order with ID {order_id}. Status: {order['status']}"
    )
    return OrderResponse(**order)

@app.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update the status of an order",
)
async def update_order_status(
    order_id: int,
    new_status: str = Query(
        ..., min_length=1, max_length=50, description="New status for the order."
    ),
):
    logger.info(
        f"Order Service: Updating status for order {order_id} to '{new_status}'"
    )
    
    if order_id not in orders_db:
        logger.warning(
            f"Order Service: Order with ID {order_id} not found for status update."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    orders_db[order_id]["status"] = new_status
    
    # Add items to the order
    order = orders_db[order_id]
    order_items = [
        OrderItemResponse(**item) 
        for item in order_items_db.values() 
        if item["order_id"] == order_id
    ]
    order["items"] = order_items

    logger.info(
        f"Order Service: Order {order_id} status updated to '{new_status}'."
    )
    return OrderResponse(**order)

@app.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order by ID",
)
def delete_order(order_id: int):
    logger.info(f"Order Service: Attempting to delete order with ID: {order_id}")
    
    if order_id not in orders_db:
        logger.warning(
            f"Order Service: Order with ID: {order_id} not found for deletion."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Delete order items first
    items_to_delete = [
        item_id for item_id, item in order_items_db.items() 
        if item["order_id"] == order_id
    ]
    for item_id in items_to_delete:
        del order_items_db[item_id]
    
    # Delete the order
    del orders_db[order_id]
    
    logger.info(f"Order Service: Order (ID: {order_id}) deleted successfully.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get(
    "/orders/{order_id}/items",
    response_model=List[OrderItemResponse],
    summary="Retrieve all items for a specific order",
)
def get_order_items(order_id: int):
    logger.info(f"Order Service: Fetching items for order ID: {order_id}")
    
    if order_id not in orders_db:
        logger.warning(
            f"Order Service: Order with ID {order_id} not found when fetching items."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    order_items = [
        OrderItemResponse(**item) 
        for item in order_items_db.values() 
        if item["order_id"] == order_id
    ]
    
    logger.info(
        f"Order Service: Retrieved {len(order_items)} items for order {order_id}."
    )
    return order_items