# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage - just copy built files to a volume
FROM alpine:latest

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Keep container running to serve the volume
CMD ["tail", "-f", "/dev/null"]
