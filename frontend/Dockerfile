FROM node:20-bookworm-slim

WORKDIR /app

# Install bun (package manager)
RUN npm i -g bun@1.1.38

# Copy only manifests for caching
COPY package.json bun.lockb ./

# Install deps
RUN bun install --frozen-lockfile

# Copy app
COPY . .

EXPOSE 3001

# Run Next using Node (NOT bun runtime)
CMD ["node", "node_modules/next/dist/bin/next", "dev", "-H", "0.0.0.0", "-p", "3001"]
