# ЭТАП 1: Сборка (Build)
FROM node:18-alpine as build-step
WORKDIR /app
COPY package.json ./

# Устанавливаем зависимости
RUN npm install
# Копируем исходный код
COPY . .
# Собираем проект (результат будет в папке dist)
RUN npm run build

# ЭТАП 2: Запуск Nginx (Production)
FROM nginx:1.25-alpine
# Копируем собранные файлы из предыдущего этапа в папку Nginx
COPY --from=build-step /app/dist /usr/share/nginx/html
# Копируем наш кастомный конфиг (см. ниже)
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Порт 80 внутри контейнера
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
