FROM nginx:alpine

COPY . /usr/share/nginx/html

# se copia el archivo de configuración personalizado de nginx para servir la aplicación correctamente
COPY nginx.conf /etc/nginx/conf.d/default.conf
