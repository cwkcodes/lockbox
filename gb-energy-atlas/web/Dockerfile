# Production image for the Next.js app (standalone output). NOTE: written alongside the app but not built in the
# authoring environment (no Docker daemon there); the same steps were run by hand: `npm ci && npm run build`, then
# `node .next/standalone/server.js` serving pages, tiles and API.
FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-bookworm-slim AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
# GeoPackage export shells out to ogr2ogr (optional); without it the GPKG option reports that it is unavailable.
RUN apt-get update && apt-get install -y --no-install-recommends gdal-bin && rm -rf /var/lib/apt/lists/*
ENV OGR2OGR_PATH=/usr/bin/ogr2ogr
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
