# syntax=docker/dockerfile:1

ARG NODE_VERSION=20-alpine
ARG NGINX_VERSION=1.27-alpine

FROM node:${NODE_VERSION} AS build
WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY package*.json ./
RUN npm ci

# Copy the rest of the frontend sources and build the production bundle
COPY . .
ARG VITE_API_BASE_URL
ARG VITE_ENVIRONMENT=production
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_ENVIRONMENT=${VITE_ENVIRONMENT}
RUN npm run build

FROM nginx:${NGINX_VERSION} AS runner
WORKDIR /usr/share/nginx/html
COPY --from=build /app/dist .

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
