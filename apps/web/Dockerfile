# ASCIIP Web — Next.js 15 standalone build.

FROM --platform=linux/amd64 node:20-bookworm-slim AS deps

RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

WORKDIR /repo

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* turbo.json ./
COPY apps/web/package.json apps/web/

RUN pnpm install --frozen-lockfile || pnpm install

# ---------------------------------------------------------------------------
FROM --platform=linux/amd64 node:20-bookworm-slim AS builder

RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

WORKDIR /repo

COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY . .

ARG NEXT_PUBLIC_API_BASE_URL=http://api:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

RUN pnpm --filter @asciip/web build

# ---------------------------------------------------------------------------
FROM --platform=linux/amd64 node:20-bookworm-slim AS runtime

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN useradd --create-home --shell /bin/bash nextjs
WORKDIR /app

COPY --from=builder --chown=nextjs:nextjs /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nextjs /repo/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 3000
CMD ["node", "apps/web/server.js"]
