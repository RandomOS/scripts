#!/bin/bash

# curl -fsSL https://raw.githubusercontent.com/RandomOS/scripts/master/shell/expose_http_server.sh | sudo bash

[[ ${DEBUG:-0} == 1 ]] && set -x

GITHUB_URL="https://github.com"
MINISERVE_VERSION="0.32.0"
CLOUDFLARED_VERSION="2025.11.1"

if [[ ! -x $(command -v miniserve) ]]; then
    rm -rf /tmp/install \
        && mkdir -p /tmp/install \
        && cd /tmp/install \
        && wget -q -O miniserve ${GITHUB_URL}/svenstaro/miniserve/releases/download/v${MINISERVE_VERSION}/miniserve-${MINISERVE_VERSION}-x86_64-unknown-linux-musl \
        && chmod +x miniserve \
        && cp -f miniserve /usr/local/bin/ \
        && cd /tmp \
        && rm -rf /tmp/install
    if [[ $? -ne 0 ]]; then
        echo "[error] download miniserve failed"
        exit
    fi
fi

if [[ ! -x $(command -v cloudflared) ]]; then
    rm -rf /tmp/install \
        && mkdir -p /tmp/install \
        && cd /tmp/install \
        && wget -q -O cloudflared ${GITHUB_URL}/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-amd64 \
        && chmod +x cloudflared \
        && cp -f cloudflared /usr/local/bin/ \
        && cd /tmp \
        && rm -rf /tmp/install
    if [[ $? -ne 0 ]]; then
        echo "[error] download cloudflared failed"
        exit
    fi
fi

mkdir -p /tmp/www
killall miniserve > /dev/null 2>&1
killall cloudflared > /dev/null 2>&1
truncate -s 0 /var/log/cloudflared.log
(miniserve -D -p 8080 /tmp/www > /dev/null 2>&1 &)
(cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8080 --logfile /var/log/cloudflared.log > /dev/null 2>&1 &)

for _ in {1..30}; do
    CF_ENDPOINT=$(grep -oP -m 1 'https://[-.\w]+\.trycloudflare\.com' /var/log/cloudflared.log | tail -n1)
    if [[ -n ${CF_ENDPOINT} ]]; then
        echo ${CF_ENDPOINT}
        break
    fi
    sleep 1
done
