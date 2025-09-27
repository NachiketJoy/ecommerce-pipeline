const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 8000;

// Middleware
app.use(cors());
app.use(express.json());

// Simple in-memory storage
let products = [];
let nextId = 1;

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'Welcome to the Product Service!' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'product-service' });
});

// Create product
app.post('/products/', (req, res) => {
  const { name, description, price, stock_quantity, image_url } = req.body;
  
  if (!name || !description || !price || !stock_quantity) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  const product = {
    product_id: nextId++,
    name,
    description,
    price: parseFloat(price),
    stock_quantity: parseInt(stock_quantity),
    image_url: image_url || null,
    created_at: new Date().toISOString()
  };

  products.push(product);
  res.status(201).json(product);
});

// Get all products
app.get('/products/', (req, res) => {
  res.json(products);
});

// Get product by ID
app.get('/products/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const product = products.find(p => p.product_id === id);
  
  if (!product) {
    return res.status(404).json({ error: 'Product not found' });
  }
  
  res.json(product);
});

// Update product
app.put('/products/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const productIndex = products.findIndex(p => p.product_id === id);
  
  if (productIndex === -1) {
    return res.status(404).json({ error: 'Product not found' });
  }

  const { name, description, price, stock_quantity, image_url } = req.body;
  
  products[productIndex] = {
    ...products[productIndex],
    name: name || products[productIndex].name,
    description: description || products[productIndex].description,
    price: price ? parseFloat(price) : products[productIndex].price,
    stock_quantity: stock_quantity ? parseInt(stock_quantity) : products[productIndex].stock_quantity,
    image_url: image_url !== undefined ? image_url : products[productIndex].image_url
  };

  res.json(products[productIndex]);
});

// Delete product
app.delete('/products/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const productIndex = products.findIndex(p => p.product_id === id);
  
  if (productIndex === -1) {
    return res.status(404).json({ error: 'Product not found' });
  }

  products.splice(productIndex, 1);
  res.json({ message: 'Product deleted successfully' });
});

// Deduct stock
app.patch('/products/:id/deduct-stock', (req, res) => {
  const id = parseInt(req.params.id);
  const { quantity_to_deduct } = req.body;
  
  const productIndex = products.findIndex(p => p.product_id === id);
  
  if (productIndex === -1) {
    return res.status(404).json({ error: 'Product not found' });
  }

  if (products[productIndex].stock_quantity < quantity_to_deduct) {
    return res.status(400).json({ 
      error: `Insufficient stock. Available: ${products[productIndex].stock_quantity}, Requested: ${quantity_to_deduct}` 
    });
  }

  products[productIndex].stock_quantity -= quantity_to_deduct;
  res.json(products[productIndex]);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Product Service running on port ${PORT}`);
});
