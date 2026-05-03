# Dockerfile — React SPA served via nginx (~30MB image)
# Used by Cloud Run "frontend" service.

# Stage 1: Build the React app
FROM node:22-alpine AS builder

WORKDIR /app

# Accept the backend API URL at build time (Vite bakes it into the bundle)
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve the built assets with nginx
FROM nginx:alpine

# Replace default nginx config with our SPA-aware config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
