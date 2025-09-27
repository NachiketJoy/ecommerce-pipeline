FROM nginx:alpine

# Copy the HTML and JS files
COPY index.html /usr/share/nginx/html/
COPY main.js /usr/share/nginx/html/

# Replace API URL placeholder with backend service URL
RUN sed -i 's/_API_URL_/http:\/\/backend-test:8000/g' /usr/share/nginx/html/main.js

# Create a simple nginx config
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api/ { \
        proxy_pass http://backend-test:8000/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]