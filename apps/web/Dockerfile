FROM node:24-alpine AS build
WORKDIR /app
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=$API_INTERNAL_URL
ARG NEXT_PUBLIC_EXPLAINER_SANDBOX_ORIGIN=http://127.0.0.1:8000
ENV NEXT_PUBLIC_EXPLAINER_SANDBOX_ORIGIN=$NEXT_PUBLIC_EXPLAINER_SANDBOX_ORIGIN
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
# A dropped registry connection (ECONNRESET) is retried instead of failing the build.
ENV npm_config_fetch_retries=5     npm_config_fetch_retry_mintimeout=10000     npm_config_fetch_retry_maxtimeout=120000
RUN npm ci
COPY apps/web apps/web
# The in-browser answer checker is the same Python file the API tests; copy-runtimes serves it.
COPY services/api/src/socrat/checks/engine.py services/api/src/socrat/checks/engine.py
RUN npm run build --workspace @socrat/web

FROM node:24-alpine AS runtime
LABEL org.opencontainers.image.source="https://github.com/Bhatta2006/Socrat"
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/apps/web ./apps/web
USER node
EXPOSE 3000
CMD ["npm", "run", "start", "--workspace", "@socrat/web"]
