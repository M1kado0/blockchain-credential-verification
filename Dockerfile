FROM node:20.19.0-bookworm-slim AS node
FROM python:3.12.10-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY package.json package-lock.json requirements.txt requirements-lock.txt ./
RUN npm ci --ignore-scripts && pip install --no-cache-dir -r requirements-lock.txt
COPY . .
RUN npm run compile && python -m pytest tests -q
CMD ["python", "-m", "src.demo"]
