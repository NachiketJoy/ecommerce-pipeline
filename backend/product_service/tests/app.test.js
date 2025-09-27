const request = require('supertest');
const app = require('../app');

describe('Product Service', () => {
  beforeEach(() => {
    // Clear products before each test
    require('../app').products = [];
    require('../app').nextId = 1;
  });

  test('GET / should return welcome message', async () => {
    const response = await request(app).get('/');
    expect(response.status).toBe(200);
    expect(response.body.message).toBe('Welcome to the Product Service!');
  });

  test('GET /health should return health status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
    expect(response.body.service).toBe('product-service');
  });

  test('POST /products/ should create a product', async () => {
    const productData = {
      name: 'Test Product',
      description: 'A test product',
      price: 29.99,
      stock_quantity: 100
    };

    const response = await request(app)
      .post('/products/')
      .send(productData);

    expect(response.status).toBe(201);
    expect(response.body.name).toBe(productData.name);
    expect(response.body.price).toBe(productData.price);
    expect(response.body.stock_quantity).toBe(productData.stock_quantity);
    expect(response.body.product_id).toBeDefined();
  });

  test('GET /products/ should return all products', async () => {
    const response = await request(app).get('/products/');
    expect(response.status).toBe(200);
    expect(Array.isArray(response.body)).toBe(true);
  });

  test('GET /products/:id should return a specific product', async () => {
    // First create a product
    const productData = {
      name: 'Test Product',
      description: 'A test product',
      price: 29.99,
      stock_quantity: 100
    };

    const createResponse = await request(app)
      .post('/products/')
      .send(productData);

    const productId = createResponse.body.product_id;

    // Then get the product
    const response = await request(app).get(`/products/${productId}`);
    expect(response.status).toBe(200);
    expect(response.body.product_id).toBe(productId);
  });

  test('GET /products/:id should return 404 for non-existent product', async () => {
    const response = await request(app).get('/products/999');
    expect(response.status).toBe(404);
    expect(response.body.error).toBe('Product not found');
  });

  test('PUT /products/:id should update a product', async () => {
    // First create a product
    const productData = {
      name: 'Test Product',
      description: 'A test product',
      price: 29.99,
      stock_quantity: 100
    };

    const createResponse = await request(app)
      .post('/products/')
      .send(productData);

    const productId = createResponse.body.product_id;

    // Then update the product
    const updateData = {
      name: 'Updated Product',
      description: 'Updated description',
      price: 39.99,
      stock_quantity: 50
    };

    const response = await request(app)
      .put(`/products/${productId}`)
      .send(updateData);

    expect(response.status).toBe(200);
    expect(response.body.name).toBe(updateData.name);
    expect(response.body.price).toBe(updateData.price);
  });

  test('DELETE /products/:id should delete a product', async () => {
    // First create a product
    const productData = {
      name: 'Test Product',
      description: 'A test product',
      price: 29.99,
      stock_quantity: 100
    };

    const createResponse = await request(app)
      .post('/products/')
      .send(productData);

    const productId = createResponse.body.product_id;

    // Then delete the product
    const response = await request(app).delete(`/products/${productId}`);
    expect(response.status).toBe(200);
    expect(response.body.message).toBe('Product deleted successfully');

    // Verify it's deleted
    const getResponse = await request(app).get(`/products/${productId}`);
    expect(getResponse.status).toBe(404);
  });

  test('PATCH /products/:id/deduct-stock should deduct stock', async () => {
    // First create a product
    const productData = {
      name: 'Test Product',
      description: 'A test product',
      price: 29.99,
      stock_quantity: 100
    };

    const createResponse = await request(app)
      .post('/products/')
      .send(productData);

    const productId = createResponse.body.product_id;

    // Then deduct stock
    const deductData = { quantity_to_deduct: 10 };
    const response = await request(app)
      .patch(`/products/${productId}/deduct-stock`)
      .send(deductData);

    expect(response.status).toBe(200);
    expect(response.body.stock_quantity).toBe(90);
  });

  test('PATCH /products/:id/deduct-stock should return 400 for insufficient stock', async () => {
    // First create a product
    const productData = {
      name: 'Test Product',
      description: 'A test product',
      price: 29.99,
      stock_quantity: 5
    };

    const createResponse = await request(app)
      .post('/products/')
      .send(productData);

    const productId = createResponse.body.product_id;

    // Then try to deduct more than available
    const deductData = { quantity_to_deduct: 10 };
    const response = await request(app)
      .patch(`/products/${productId}/deduct-stock`)
      .send(deductData);

    expect(response.status).toBe(400);
    expect(response.body.error).toContain('Insufficient stock');
  });
});
