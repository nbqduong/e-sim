# Production-ready Dockerfile for Next.js
# See: https://nextjs.org/docs/pages/building-your-application/deploying#docker-image

# 1. Install dependencies only when needed
FROM node:20-alpine AS deps
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json package-lock.json* ./
RUN npm ci

# 2. Rebuild the source code only when needed
FROM node:20-alpine AS builder

USER node

ENV APP_DIR=/home/node/source
WORKDIR ${APP_DIR}

COPY --from=deps --chown=node:node /app/node_modules ./node_modules

# Next.js collects completely anonymous telemetry data about general usage.
# Learn more here: https://nextjs.org/telemetry
ENV NEXT_TELEMETRY_DISABLED=1

# 3. Start the application
CMD ["sh", "./build.sh"]
