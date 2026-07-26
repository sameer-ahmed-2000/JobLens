# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package configuration
COPY package*.json ./

# Install all dependencies
RUN npm ci

# Copy source code files
COPY . .

# Build-time argument for API URL
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

# Build the React application
RUN npm run build

# Production runtime stage
FROM nginx:alpine

# Copy built frontend assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration for SPA routing support
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
