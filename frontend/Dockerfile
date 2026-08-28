FROM node:20-alpine

WORKDIR /app

# Install deps first (layer caching)
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

EXPOSE 5173

# Vite dev server — binds to 0.0.0.0 so Nginx can reach it
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
