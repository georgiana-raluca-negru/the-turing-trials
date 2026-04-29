# 1. Base Image: Use an official, lightweight Node.js image
FROM node:20-alpine

# 2. Set the Working Directory
WORKDIR /app

# 3. Copy the package files first
COPY package.json package-lock.json ./

# 4. Install the Node modules
RUN npm install

# 5. Copy the rest of the Next.js code
COPY . .

# 6. Build the application for production
RUN npm run build

# 7. Expose the port Next.js uses
EXPOSE 3000

# 8. Start the production server
CMD ["npm", "start"]