const request = require('supertest');
const app = require('../app');

// Mock axios
jest.mock('axios');
const axios = require('axios');

describe('Order Service', () => {
  beforeEach(() => {
    // Clear orders before each test
    require('../app').orders = [];
    require('../app').nextOrderId = 1;
    require('../app').nextItemId = 1;
    
    // Reset axios mock
    jest.clearAllMocks();
  });

  test('GET / should return welcome message', async () => {
    const response = await request(app).get('/');
    expect(response.status).toBe(200);
    expect(response.body.message).toBe('Welcome to the Order Service!');
  });

  test('GET /health should return health status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
    expect(response.body.service).toBe('order-service');
  });

  test('POST /orders/ should create an order successfully', async () => {
    // Mock successful stock deduction
    axios.patch.mockResolvedValue({ status: 200 });

    const orderData = {
      user_id: 1,
      shipping_address: '123 Test St',
      items: [
        {
          product_id: 'test-product-id',
          quantity: 2,
          price_at_purchase: 29.99
        }
      ]
    };

    const response = await request(app)
      .post('/orders/')
      .send(orderData);

    expect(response.status).toBe(201);
    expect(response.body.user_id).toBe(1);
    expect(response.body.status).toBe('confirmed');
    expect(response.body.total_amount).toBe(59.98);
    expect(response.body.items).toHaveLength(1);
  });

  test('POST /orders/ should return 400 for empty items', async () => {
    const orderData = {
      user_id: 1,
      shipping_address: '123 Test St',
      items: []
    };

    const response = await request(app)
      .post('/orders/')
      .send(orderData);

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('Order must contain at least one item');
  });

  test('POST /orders/ should return 400 for insufficient stock', async () => {
    // Mock insufficient stock response
    axios.patch.mockRejectedValue({
      response: { status: 400 }
    });

    const orderData = {
      user_id: 1,
      shipping_address: '123 Test St',
      items: [
        {
          product_id: 'test-product-id',
          quantity: 2,
          price_at_purchase: 29.99
        }
      ]
    };

    const response = await request(app)
      .post('/orders/')
      .send(orderData);

    expect(response.status).toBe(400);
    expect(response.body.error).toContain('Insufficient stock');
  });

  test('GET /orders/ should return all orders', async () => {
    const response = await request(app).get('/orders/');
    expect(response.status).toBe(200);
    expect(Array.isArray(response.body)).toBe(true);
  });

  test('GET /orders/:id should return a specific order', async () => {
    // First create an order
    axios.patch.mockResolvedValue({ status: 200 });

    const orderData = {
      user_id: 1,
      shipping_address: '123 Test St',
      items: [
        {
          product_id: 'test-product-id',
          quantity: 1,
          price_at_purchase: 29.99
        }
      ]
    };

    const createResponse = await request(app)
      .post('/orders/')
      .send(orderData);

    const orderId = createResponse.body.order_id;

    // Then get the order
    const response = await request(app).get(`/orders/${orderId}`);
    expect(response.status).toBe(200);
    expect(response.body.order_id).toBe(orderId);
  });

  test('GET /orders/:id should return 404 for non-existent order', async () => {
    const response = await request(app).get('/orders/999');
    expect(response.status).toBe(404);
    expect(response.body.error).toBe('Order not found');
  });

  test('PATCH /orders/:id/status should update order status', async () => {
    // First create an order
    axios.patch.mockResolvedValue({ status: 200 });

    const orderData = {
      user_id: 1,
      shipping_address: '123 Test St',
      items: [
        {
          product_id: 'test-product-id',
          quantity: 1,
          price_at_purchase: 29.99
        }
      ]
    };

    const createResponse = await request(app)
      .post('/orders/')
      .send(orderData);

    const orderId = createResponse.body.order_id;

    // Then update status
    const response = await request(app)
      .patch(`/orders/${orderId}/status?new_status=shipped`);

    expect(response.status).toBe(200);
    expect(response.body.status).toBe('shipped');
  });

  test('DELETE /orders/:id should delete an order', async () => {
    // First create an order
    axios.patch.mockResolvedValue({ status: 200 });

    const orderData = {
      user_id: 1,
      shipping_address: '123 Test St',
      items: [
        {
          product_id: 'test-product-id',
          quantity: 1,
          price_at_purchase: 29.99
        }
      ]
    };

    const createResponse = await request(app)
      .post('/orders/')
      .send(orderData);

    const orderId = createResponse.body.order_id;

    // Then delete the order
    const response = await request(app).delete(`/orders/${orderId}`);
    expect(response.status).toBe(200);
    expect(response.body.message).toBe('Order deleted successfully');

    // Verify it's deleted
    const getResponse = await request(app).get(`/orders/${orderId}`);
    expect(getResponse.status).toBe(404);
  });

  test('GET /orders/:id/items should return order items', async () => {
    // First create an order
    axios.patch.mockResolvedValue({ status: 200 });

    const orderData = {
      user_id: 1,
      shipping_address: '123 Test St',
      items: [
        {
          product_id: 'test-product-id',
          quantity: 2,
          price_at_purchase: 29.99
        }
      ]
    };

    const createResponse = await request(app)
      .post('/orders/')
      .send(orderData);

    const orderId = createResponse.body.order_id;

    // Then get order items
    const response = await request(app).get(`/orders/${orderId}/items`);
    expect(response.status).toBe(200);
    expect(Array.isArray(response.body)).toBe(true);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].product_id).toBe('test-product-id');
  });
});
