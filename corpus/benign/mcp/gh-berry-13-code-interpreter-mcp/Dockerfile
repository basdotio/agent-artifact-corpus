FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json tsconfig.json ./
COPY src ./src
RUN npm ci && npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY package*.json ./
RUN npm ci --only=production

ENV LIBRECHAT_API_KEY=""

ENTRYPOINT ["node", "dist/index.js"]