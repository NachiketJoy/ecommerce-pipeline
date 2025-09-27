# Simplified Product Service - API Only

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlparse

# Azure Storage Imports
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ProductCreate, ProductResponse, ProductUpdate, StockDeductRequest

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

AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONTAINER_NAME = os.getenv(
    "AZURE_STORAGE_CONTAINER_NAME", "product-images"
)
AZURE_SAS_TOKEN_EXPIRY_HOURS = int(os.getenv("AZURE_SAS_TOKEN_EXPIRY_HOURS", "24"))

# Initialize BlobServiceClient
if AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY:
    try:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=AZURE_STORAGE_ACCOUNT_KEY,
        )
        logger.info("Product Service: Azure BlobServiceClient initialized.")
        # Ensure the container exists
        try:
            container_client = blob_service_client.get_container_client(
                AZURE_STORAGE_CONTAINER_NAME
            )
            container_client.create_container()
            logger.info(
                f"Product Service: Azure container '{AZURE_STORAGE_CONTAINER_NAME}' ensured to exist."
            )
        except Exception as e:
            logger.warning(
                f"Product Service: Could not create or verify Azure container '{AZURE_STORAGE_CONTAINER_NAME}'. It might already exist. Error: {e}"
            )
    except Exception as e:
        logger.critical(
            f"Product Service: Failed to initialize Azure BlobServiceClient. Check credentials and account name. Error: {e}",
            exc_info=True,
        )
        blob_service_client = None  # Set to None if initialization fails
else:
    logger.warning(
        "Product Service: Azure Storage credentials not found. Image upload functionality will be disabled."
    )
    blob_service_client = None

RESTOCK_THRESHOLD = 5  # Threshold for restock notification

# In-memory storage for products
products_db = {}
next_product_id = 1

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Product Service API",
    description="Manages products and stock for mini-ecommerce app, with Azure Storage integration.",
    version="1.0.0",
)

# Enable CORS (for frontend dev/testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root Endpoint ---
@app.get("/", status_code=status.HTTP_200_OK, summary="Root endpoint")
async def read_root():
    return {"message": "Welcome to the Product Service!"}

# --- Health Check Endpoint ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "service": "product-service"}

@app.post(
    "/products/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(product: ProductCreate):
    """
    Creates a new product in memory.
    """
    global next_product_id
    logger.info(f"Product Service: Creating product: {product.name}")
    
    product_data = product.model_dump()
    product_data["product_id"] = next_product_id
    product_data["created_at"] = datetime.now()
    
    products_db[next_product_id] = product_data
    next_product_id += 1
    
    logger.info(
        f"Product Service: Product '{product_data['name']}' (ID: {product_data['product_id']}) created successfully."
    )
    return ProductResponse(**product_data)

@app.get(
    "/products/",
    response_model=List[ProductResponse],
    summary="Retrieve a list of all products",
)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=255),
):
    """
    Lists products with optional pagination and search by name/description.
    """
    logger.info(
        f"Product Service: Listing products with skip={skip}, limit={limit}, search='{search}'"
    )
    
    products = list(products_db.values())
    
    if search:
        search_pattern = search.lower()
        logger.info(f"Product Service: Applying search filter for term: {search}")
        products = [
            p for p in products 
            if search_pattern in p["name"].lower() or 
               (p["description"] and search_pattern in p["description"].lower())
        ]
    
    # Apply pagination
    products = products[skip:skip + limit]
    
    logger.info(
        f"Product Service: Retrieved {len(products)} products (skip={skip}, limit={limit})."
    )
    return [ProductResponse(**product) for product in products]

@app.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Retrieve a single product by ID",
)
def get_product(product_id: int):
    logger.info(f"Product Service: Fetching product with ID: {product_id}")
    
    if product_id not in products_db:
        logger.warning(f"Product Service: Product with ID {product_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    
    product = products_db[product_id]
    logger.info(
        f"Product Service: Retrieved product with ID {product_id}. Name: {product['name']}"
    )
    return ProductResponse(**product)

@app.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update an existing product by ID",
)
async def update_product(product_id: int, product: ProductUpdate):
    logger.info(
        f"Product Service: Updating product with ID: {product_id} with data: {product.model_dump(exclude_unset=True)}"
    )
    
    if product_id not in products_db:
        logger.warning(
            f"Product Service: Attempted to update non-existent product with ID {product_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        products_db[product_id][key] = value

    logger.info(f"Product Service: Product {product_id} updated successfully.")
    return ProductResponse(**products_db[product_id])

@app.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product by ID",
)
def delete_product(product_id: int):
    """
    Deletes a product record from memory.
    Does NOT delete the image from Azure Blob Storage.
    """
    logger.info(f"Product Service: Attempting to delete product with ID: {product_id}")
    
    if product_id not in products_db:
        logger.warning(
            f"Product Service: Attempted to delete non-existent product with ID {product_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    product_name = products_db[product_id]["name"]
    del products_db[product_id]
    
    logger.info(
        f"Product Service: Product {product_id} deleted successfully. Name: {product_name}"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post(
    "/products/{product_id}/upload-image",
    response_model=ProductResponse,
    summary="Upload an image for a product to Azure Blob Storage",
)
async def upload_product_image(
    product_id: int, file: UploadFile = File(...)
):
    """
    Uploads an image file to Azure Blob Storage and updates the product's image_url in memory.
    Generates a SAS token for the image URL with a defined expiry.
    Only supports image file types.
    """
    if not blob_service_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure Blob Storage is not configured or available.",
        )

    if product_id not in products_db:
        logger.warning(
            f"Product Service: Product with ID {product_id} not found for image upload."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Basic file type validation
    allowed_content_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(allowed_content_types)} are allowed.",
        )

    try:
        # Create a unique blob name (e.g., product_id/timestamp_originalfilename.ext)
        file_extension = (
            os.path.splitext(file.filename)[1]
            if os.path.splitext(file.filename)[1]
            else ".jpg"
        )  # Ensure extension
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        blob_name = f"{timestamp}{file_extension}"

        blob_client = blob_service_client.get_blob_client(
            container=AZURE_STORAGE_CONTAINER_NAME, blob=blob_name
        )

        logger.info(
            f"Product Service: Uploading image '{file.filename}' for product {product_id} as '{blob_name}' to Azure."
        )

        # Upload the file content directly
        blob_client.upload_blob(
            file.file,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type),
        )

        # Generate Shared Access Signature (SAS) for public read access
        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT_NAME,
            account_key=AZURE_STORAGE_ACCOUNT_KEY,
            container_name=AZURE_STORAGE_CONTAINER_NAME,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=AZURE_SAS_TOKEN_EXPIRY_HOURS),
        )
        # Construct the full URL with SAS token
        image_url = f"{blob_client.url}?{sas_token}"

        # Update the product in memory with the image URL (including SAS token)
        products_db[product_id]["image_url"] = image_url

        logger.info(
            f"Product Service: Image uploaded and product {product_id} updated with SAS URL: {image_url}"
        )
        return ProductResponse(**products_db[product_id])

    except Exception as e:
        logger.error(
            f"Product Service: Error uploading image for product {product_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload image or update product: {e}",
        )

# --- Endpoint for Stock Deduction ---
@app.patch(
    "/products/{product_id}/deduct-stock",
    response_model=ProductResponse,
    summary="Deduct stock quantity for a product",
)
async def deduct_product_stock(
    product_id: int, request: StockDeductRequest
):
    """
    Deducts a specified quantity from a product's stock.
    Returns 404 if product not found, 400 if insufficient stock.
    """
    logger.info(
        f"Product Service: Attempting to deduct {request.quantity_to_deduct} from stock for product ID: {product_id}"
    )
    
    if product_id not in products_db:
        logger.warning(
            f"Product Service: Stock deduction failed: Product with ID {product_id} not found."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    product = products_db[product_id]
    if product["stock_quantity"] < request.quantity_to_deduct:
        logger.warning(
            f"Product Service: Stock deduction failed for product {product_id}. Insufficient stock: {product['stock_quantity']} available, {request.quantity_to_deduct} requested."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock for product '{product['name']}'. Only {product['stock_quantity']} available.",
        )

    # Perform deduction
    product["stock_quantity"] -= request.quantity_to_deduct
    
    logger.info(
        f"Product Service: Stock for product {product_id} updated to {product['stock_quantity']}. Deducted {request.quantity_to_deduct}."
    )

    # Optional: Log or trigger alert if stock falls below threshold
    if product["stock_quantity"] < RESTOCK_THRESHOLD:
        logger.warning(
            f"Product Service: ALERT! Stock for product '{product['name']}' (ID: {product_id}) is low: {product['stock_quantity']}."
        )

    return ProductResponse(**product)