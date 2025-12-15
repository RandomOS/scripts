#!/bin/bash

# curl -fsSL -o /tmp/expose_http_server.sh https://raw.githubusercontent.com/RandomOS/scripts/master/shell/expose_http_server.sh && bash /tmp/expose_http_server.sh

[[ ${DEBUG:-0} == 1 ]] && set -x

GITHUB_URL="https://github.com"
MINISERVE_VERSION="0.32.0"

if [[ ! -x $(command -v miniserve) ]]; then
    rm -rf /tmp/install \
        && mkdir -p /tmp/install \
        && cd /tmp/install \
        && wget -q -O miniserve ${GITHUB_URL}/svenstaro/miniserve/releases/download/v${MINISERVE_VERSION}/miniserve-${MINISERVE_VERSION}-x86_64-unknown-linux-musl \
        && chmod +x miniserve \
        && sudo cp -f miniserve /usr/local/bin/ \
        && cd /tmp \
        && rm -rf /tmp/install
    if [[ $? -ne 0 ]]; then
        echo "[error] download failed"
        exit
    fi
fi

mkdir -p /tmp/www
killall miniserve >/dev/null 2>&1
(miniserve -D -p 8080 /tmp/www >/dev/null 2>&1 &)

ssh -o StrictHostKeyChecking=no -t -R 80:localhost:8080 proxy.tunnl.gg
