FROM node:20-alpine

WORKDIR /app

# Install dependencies before copying source
# This layer is cached when only source files change
COPY package*.json ./
RUN npm ci --only=production

COPY src/ ./src/

RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q -O- http://localhost:8004/health || exit 1

CMD ["node", "src/index.js"]
