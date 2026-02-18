# Frontend Dockerfile
FROM node:20-alpine

WORKDIR /app

# Enable pnpm via Corepack
RUN corepack enable && corepack prepare pnpm@9.0.0 --activate

# Install dependencies first (leverage cache)
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Build args for public runtime config
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Copy source
COPY . .

# Build Next.js app
RUN pnpm build

EXPOSE 3000
CMD ["pnpm", "start", "--port", "3000", "--hostname", "0.0.0.0"]
