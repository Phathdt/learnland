# syntax=docker/dockerfile:1

# --- Build stage ---
FROM node:24-alpine AS build

WORKDIR /app

RUN corepack enable

# Install dependencies first for better layer caching.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Backend URL is baked into the bundle at build time. Vite reads it from the
# committed .env file — do NOT set VITE_API_URL as a shell/ENV var here, since
# OS env vars take priority over .env and would silently override it.
COPY . .
RUN pnpm build

# --- Runtime stage ---
FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
