FROM node:20-alpine

WORKDIR /app

ARG NEXT_PUBLIC_API_BASE_URL=/api
ARG BACKEND_INTERNAL_URL=http://backend-api:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}

COPY package.json /app/package.json
RUN npm install

COPY . /app

RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
