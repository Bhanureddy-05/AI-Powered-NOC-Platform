# Multi-stage static build configuration
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Runner stage with lightweight Nginx web server
FROM nginx:1.25-alpine AS runner

# Copy static built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy default nginx configuration if needed, or rely on defaults
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
