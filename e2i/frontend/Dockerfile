# Frontend Dockerfile for Railway deployment
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm
RUN pnpm install

# Copy source code
COPY . .

# Set environment variables for production build
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false

# Build the application
RUN pnpm build

# Install serve to run the production build
RUN npm install -g serve

# Expose port (Railway will set PORT environment variable)
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/ || exit 1

# Start the application
CMD ["sh", "-c", "serve -s build -l $PORT"]