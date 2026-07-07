# --- Build stage ---
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked in at build time (Vite inlines env vars into the bundle). Leave unset
# to keep API calls relative (/api/...) and let nginx proxy them at runtime
# via BACKEND_ORIGIN instead — see nginx.conf.template.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- Runtime stage ---
FROM nginx:1.27-alpine

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

# Where the backend API lives at runtime; nginx proxies /api/* here.
# Override via `docker run -e BACKEND_ORIGIN=...` or docker-compose.yml.
ENV BACKEND_ORIGIN="http://localhost:8080"

EXPOSE 80
