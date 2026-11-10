# syntax=docker/dockerfile:1

# --- Zależności (wspólne dla dev i build) ---
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# --- Tryb deweloperski: serwer Vite z hot reload (używany przez docker-compose.override.yml) ---
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# --- Build produkcyjny ---
FROM deps AS build
COPY . .
RUN npm run build

# --- Produkcja: nginx serwuje statyczne pliki i przekierowuje /api do backendu ---
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
