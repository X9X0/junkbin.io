# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Pass OAuth client IDs and dev tools flag for Vite build
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
ARG VITE_GITHUB_CLIENT_ID
ENV VITE_GITHUB_CLIENT_ID=$VITE_GITHUB_CLIENT_ID
ARG VITE_DEV_TOOLS
ENV VITE_DEV_TOOLS=$VITE_DEV_TOOLS
ARG VITE_SENTRY_DSN
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN
ARG VITE_SENTRY_ENVIRONMENT
ENV VITE_SENTRY_ENVIRONMENT=$VITE_SENTRY_ENVIRONMENT
ARG VITE_GIT_SHA
ENV VITE_GIT_SHA=$VITE_GIT_SHA

# Build the application
RUN npm run build

# Production stage - just copy built files to a volume
FROM alpine:latest

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Keep container running to serve the volume
CMD ["tail", "-f", "/dev/null"]
