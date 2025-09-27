const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 8000;

// Middleware
app.use(cors());
app.use(express.json());

// Configuration
const PRODUCT_SERVICE_URL = process.env.PRODUCT_SERVICE_URL || 'http://product-service:8000';

// Simple in-memory storage
let orders = [];
let nextOrderId = 1;
let nextItemId = 1;

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'Welcome to the Order Service!' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'order-service' });
});

// Create order
app.post('/orders/', async (req, res) => {
  try {
    const { user_id, shipping_address, items } = req.body;
    
    if (!items || items.length === 0) {
      return res.status(400).json({ error: 'Order must contain at least one item' });
    }

    const order_id = nextOrderId++;
    let total_amount = 0;
    const order_items = [];

    // Process each item
    for (const item of items) {
      try {
        // Deduct stock from product service
        const deductResponse = await axios.patch(
          `${PRODUCT_SERVICE_URL}/products/${item.product_id}/deduct-stock`,
          { quantity_to_deduct: item.quantity },
          { timeout: 5000 }
        );
      } catch (error) {
        if (error.response && error.response.status === 400) {
          return res.status(400).json({ error: `Insufficient stock for product ${item.product_id}` });
        } else if (error.response && error.response.status === 404) {
          return res.status(400).json({ error: `Product ${item.product_id} not found` });
        } else {
          return res.status(503).json({ error: 'Product service unavailable' });
        }
      }

      // Create order item
      const item_id = nextItemId++;
      const item_total = item.quantity * item.price_at_purchase;
      total_amount += item_total;

      const order_item = {
        order_item_id: item_id,
        order_id: order_id,
        product_id: item.product_id,
        quantity: item.quantity,
        price_at_purchase: item.price_at_purchase,
        item_total: item_total,
        created_at: new Date().toISOString()
      };
      order_items.push(order_item);
    }

    // Create order
    const order = {
      order_id: order_id,
      user_id: user_id,
      shipping_address: shipping_address,
      status: 'confirmed',
      total_amount: total_amount,
      items: order_items,
      order_date: new Date().toISOString()
    };

    orders.push(order);
    res.status(201).json(order);

  } catch (error) {
    console.error('Error creating order:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get all orders
app.get('/orders/', (req, res) => {
  res.json(orders);
});

// Get order by ID
app.get('/orders/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const order = orders.find(o => o.order_id === id);
  
  if (!order) {
    return res.status(404).json({ error: 'Order not found' });
  }
  
  res.json(order);
});

// Update order status
app.patch('/orders/:id/status', (req, res) => {
  const id = parseInt(req.params.id);
  const { new_status } = req.query;
  
  const orderIndex = orders.findIndex(o => o.order_id === id);
  
  if (orderIndex === -1) {
    return res.status(404).json({ error: 'Order not found' });
  }

  orders[orderIndex].status = new_status;
  res.json(orders[orderIndex]);
});

// Delete order
app.delete('/orders/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const orderIndex = orders.findIndex(o => o.order_id === id);
  
  if (orderIndex === -1) {
    return res.status(404).json({ error: 'Order not found' });
  }

  orders.splice(orderIndex, 1);
  res.json({ message: 'Order deleted successfully' });
});

// Get order items
app.get('/orders/:id/items', (req, res) => {
  const id = parseInt(req.params.id);
  const order = orders.find(o => o.order_id === id);
  
  if (!order) {
    return res.status(404).json({ error: 'Order not found' });
  }
  
  res.json(order.items);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Order Service running on port ${PORT}`);
});
