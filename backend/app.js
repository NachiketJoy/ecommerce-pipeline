const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 8000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// In-memory data storage (for simplicity)
let products = [
    {
        product_id: 1,
        name: "Sample Product 1",
        description: "This is a sample product",
        price: 29.99,
        stock_quantity: 10,
        image_url: "https://placehold.co/300x200/cccccc/333333?text=Sample+Product+1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    },
    {
        product_id: 2,
        name: "Sample Product 2",
        description: "Another sample product",
        price: 49.99,
        stock_quantity: 5,
        image_url: "https://placehold.co/300x200/cccccc/333333?text=Sample+Product+2",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    }
];

let orders = [];
let nextProductId = 3;
let nextOrderId = 1;

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Product endpoints
app.get('/products/', (req, res) => {
    res.json(products);
});

app.post('/products/', (req, res) => {
    const { name, price, stock_quantity, description } = req.body;
    
    if (!name || !price || !stock_quantity) {
        return res.status(400).json({ 
            detail: 'Missing required fields: name, price, stock_quantity' 
        });
    }

    const newProduct = {
        product_id: nextProductId++,
        name,
        description: description || '',
        price: parseFloat(price),
        stock_quantity: parseInt(stock_quantity),
        image_url: "https://placehold.co/300x200/cccccc/333333?text=No+Image",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    };

    products.push(newProduct);
    res.status(201).json(newProduct);
});

app.delete('/products/:id', (req, res) => {
    const productId = parseInt(req.params.id);
    const productIndex = products.findIndex(p => p.product_id === productId);
    
    if (productIndex === -1) {
        return res.status(404).json({ detail: 'Product not found' });
    }

    products.splice(productIndex, 1);
    res.status(204).send();
});

app.post('/products/:id/upload-image', (req, res) => {
    const productId = parseInt(req.params.id);
    const product = products.find(p => p.product_id === productId);
    
    if (!product) {
        return res.status(404).json({ detail: 'Product not found' });
    }

    // For simplicity, just return a placeholder image URL
    // In a real application, you would handle file upload here
    product.image_url = `https://placehold.co/300x200/cccccc/333333?text=Product+${productId}`;
    product.updated_at = new Date().toISOString();
    
    res.json(product);
});

// Order endpoints
app.get('/orders/', (req, res) => {
    res.json(orders);
});

app.post('/orders/', (req, res) => {
    const { user_id, shipping_address, items } = req.body;
    
    if (!user_id || !shipping_address || !items || !Array.isArray(items)) {
        return res.status(400).json({ 
            detail: 'Missing required fields: user_id, shipping_address, items' 
        });
    }

    // Calculate total amount
    let totalAmount = 0;
    const orderItems = items.map(item => {
        const product = products.find(p => p.product_id === item.product_id);
        if (!product) {
            throw new Error(`Product with ID ${item.product_id} not found`);
        }
        
        // Update stock
        if (product.stock_quantity < item.quantity) {
            throw new Error(`Insufficient stock for product ${product.name}`);
        }
        product.stock_quantity -= item.quantity;
        product.updated_at = new Date().toISOString();
        
        const itemTotal = item.quantity * item.price_at_purchase;
        totalAmount += itemTotal;
        
        return {
            product_id: item.product_id,
            quantity: item.quantity,
            price_at_purchase: item.price_at_purchase,
            item_total: itemTotal
        };
    });

    const newOrder = {
        order_id: nextOrderId++,
        user_id: parseInt(user_id),
        order_date: new Date().toISOString(),
        status: 'pending',
        total_amount: totalAmount,
        shipping_address,
        items: orderItems,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    };

    orders.push(newOrder);
    res.status(201).json(newOrder);
});

app.patch('/orders/:id/status', (req, res) => {
    const orderId = parseInt(req.params.id);
    const { new_status } = req.query;
    
    const order = orders.find(o => o.order_id === orderId);
    if (!order) {
        return res.status(404).json({ detail: 'Order not found' });
    }

    const validStatuses = ['pending', 'processing', 'shipped', 'confirmed', 'cancelled', 'completed'];
    if (!validStatuses.includes(new_status)) {
        return res.status(400).json({ 
            detail: `Invalid status. Must be one of: ${validStatuses.join(', ')}` 
        });
    }

    order.status = new_status;
    order.updated_at = new Date().toISOString();
    
    res.json(order);
});

app.delete('/orders/:id', (req, res) => {
    const orderId = parseInt(req.params.id);
    const orderIndex = orders.findIndex(o => o.order_id === orderId);
    
    if (orderIndex === -1) {
        return res.status(404).json({ detail: 'Order not found' });
    }

    orders.splice(orderIndex, 1);
    res.status(204).send();
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ detail: err.message });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ detail: 'Endpoint not found' });
});

// Export app for testing
module.exports = app;

// Start server (always start for Docker containers)
if (!module.parent) {
    app.listen(PORT, () => {
        console.log(`E-commerce API server running on port ${PORT}`);
        console.log(`Health check: http://localhost:${PORT}/health`);
        console.log(`Products: http://localhost:${PORT}/products/`);
        console.log(`Orders: http://localhost:${PORT}/orders/`);
    });
}
