FROM nginx:alpine

# Install dos2unix to ensure Linux format
RUN apk add --no-cache dos2unix

# Remove default Nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy frontend configuration and static HTML
COPY default.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html

# Fix Windows CRLF line endings
RUN dos2unix /etc/nginx/conf.d/default.conf /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]