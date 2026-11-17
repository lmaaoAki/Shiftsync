FROM nginx:alpine

RUN apk add --no-cache dos2unix

RUN rm -f /etc/nginx/conf.d/default.conf

COPY default.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY styles.css /usr/share/nginx/html/styles.css

RUN dos2unix /etc/nginx/conf.d/default.conf /usr/share/nginx/html/index.html /usr/share/nginx/html/styles.css

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]