FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG API_URL=http://api:8000
ENV API_URL=$API_URL
RUN npm run build
CMD ["npm", "start"]
