FROM node:20-slim AS builder

WORKDIR /app
COPY package*.json ./
# NODE_ENV=production causes npm ci to skip devDependencies (which includes tsc/vite)
RUN NODE_ENV=development npm ci
COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
