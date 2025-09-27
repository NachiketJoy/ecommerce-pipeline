const request = require('supertest');
const app = require('../app');

describe('E-commerce API', () => {
    describe('Health Check', () => {
        test('GET /health should return healthy status', async () => {
            const response = await request(app)
                .get('/health')
                .expect(200);
            
            expect(response.body.status).toBe('healthy');
            expect(response.body.timestamp).toBeDefined();
        });
    });

    describe('Products', () => {
        test('GET /products/ should return products list', async () => {
            const response = await request(app)
                .get('/products/')
                .expect(200);
            
            expect(Array.isArray(response.body)).toBe(true);
            expect(response.body.length).toBeGreaterThan(0);
        });

        test('POST /products/ should create a new product', async () => {
            const newProduct = {
                name: 'Test Product',
                price: 19.99,
                stock_quantity: 5,
                description: 'A test product'
            };

            const response = await request(app)
                .post('/products/')
                .send(newProduct)
                .expect(201);
            
            expect(response.body.name).toBe(newProduct.name);
            expect(response.body.price).toBe(newProduct.price);
            expect(response.body.stock_quantity).toBe(newProduct.stock_quantity);
            expect(response.body.product_id).toBeDefined();
        });

        test('POST /products/ should return 400 for missing fields', async () => {
            const incompleteProduct = {
                name: 'Test Product'
                // Missing price and stock_quantity
            };

            await request(app)
                .post('/products/')
                .send(incompleteProduct)
                .expect(400);
        });
    });

    describe('Orders', () => {
        test('GET /orders/ should return orders list', async () => {
            const response = await request(app)
                .get('/orders/')
                .expect(200);
            
            expect(Array.isArray(response.body)).toBe(true);
        });

        test('POST /orders/ should create a new order', async () => {
            const newOrder = {
                user_id: 1,
                shipping_address: '123 Test St, Test City',
                items: [
                    {
                        product_id: 1,
                        quantity: 2,
                        price_at_purchase: 29.99
                    }
                ]
            };

            const response = await request(app)
                .post('/orders/')
                .send(newOrder)
                .expect(201);
            
            expect(response.body.user_id).toBe(newOrder.user_id);
            expect(response.body.shipping_address).toBe(newOrder.shipping_address);
            expect(response.body.total_amount).toBe(59.98);
            expect(response.body.order_id).toBeDefined();
        });

        test('POST /orders/ should return 400 for missing fields', async () => {
            const incompleteOrder = {
                user_id: 1
                // Missing shipping_address and items
            };

            await request(app)
                .post('/orders/')
                .send(incompleteOrder)
                .expect(400);
        });
    });
});
