#!/bin/sh
set -e

DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
ENABLE_HTTPS="${ENABLE_HTTPS:-false}"

echo "=========================================================="
echo "HealthWatch API Gateway & Reverse Proxy Initializing"
echo "Target Domain: ${DOMAIN_NAME}"
echo "HTTPS Enabled: ${ENABLE_HTTPS}"
echo "=========================================================="

CERT_PATH="/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem"

if [ "${ENABLE_HTTPS}" = "true" ] && [ -f "${CERT_PATH}" ]; then
    echo "SSL Certificate detected at ${CERT_PATH}. Applying HTTPS configuration."
    envsubst '${DOMAIN_NAME}' < /etc/nginx/templates/nginx-ssl.conf.template > /etc/nginx/conf.d/default.conf
else
    if [ "${ENABLE_HTTPS}" = "true" ]; then
        echo "Notice: ENABLE_HTTPS is true, but ${CERT_PATH} was not found."
        echo "Starting in HTTP mode first so ACME / Certbot can obtain the certificate."
    else
        echo "Starting in standard HTTP mode (No SSL)."
    fi
    envsubst '${DOMAIN_NAME}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf
fi

echo "Configuration generated successfully. Starting Nginx..."
exec nginx -g "daemon off;"
