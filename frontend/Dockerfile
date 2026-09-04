FROM node:20-alpine

WORKDIR /app

# Copy package descriptors
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source
COPY . .

# Expose Vite dev port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev"]
