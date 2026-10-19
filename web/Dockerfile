# Vaani web page image (Next.js, from LiveKit's starter).
# Build from the web folder:  docker build web
#
# Expects (created in Phase 1): web/package.json and web/pnpm-lock.yaml.
# Settings come from web/.env at run time; NEXT_PUBLIC_ values are read
# at build time, so never put a secret behind NEXT_PUBLIC_.

FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM node:22-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable && adduser -D -u 10001 vaani
COPY --from=build /app ./
USER vaani
EXPOSE 3000
CMD ["pnpm", "start"]
