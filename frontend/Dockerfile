FROM oven/bun:1.1.0

WORKDIR /app

# Copy only manifests for caching
COPY package.json bun.lockb ./

# Install deps (cached layer)
RUN bun install --frozen-lockfile

# Copy app
COPY . .

# Next dev server must bind 0.0.0.0 and use port 3001 for your Caddyfile
EXPOSE 3001

CMD ["bun", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3001"]
