# ==============================================================================
# HealthWatch Gateway - Nginx Reverse Proxy Microservice
# Dynamically configures HTTP or HTTPS reverse proxy for any domain
# ==============================================================================

FROM nginx:alpine

# Remove default config
RUN rm -rf /etc/nginx/conf.d/default.conf /usr/share/nginx/html/*

# Create template and challenge directories
RUN mkdir -p /etc/nginx/templates /var/www/certbot /etc/letsencrypt

# Copy templates and entrypoint
COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY nginx-ssl.conf.template /etc/nginx/templates/nginx-ssl.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose HTTP (80) and HTTPS (443)
EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
