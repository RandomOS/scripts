#!/bin/sh

# curl -fsSL https://raw.githubusercontent.com/RandomOS/scripts/master/shell/chisel.sh | sh

CHISEL_VERSION="1.9.0"

PATH="$PATH:."
WORK_DIR="/tmp/chisel"

mkdir -p $WORK_DIR && cd $WORK_DIR

if [ ! -x $WORK_DIR/chisel ]; then
    wget -q -O chisel.gz https://github.com/jpillora/chisel/releases/download/v${CHISEL_VERSION}/chisel_${CHISEL_VERSION}_linux_amd64.gz \
        && gzip -d chisel.gz \
        && chmod +x chisel
fi

if [ ! -x $WORK_DIR/cloudflared ]; then
    wget -q -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
        && chmod +x cloudflared
fi

truncate -s 0 cloudflared.log

pkill -x chisel
pkill -x cloudflared
(chisel server --host 127.0.0.1 --port 54321 --auth chisel:chisel --socks5 --backend http://example.com >/dev/null 2>&1 &)
(cloudflared tunnel --no-autoupdate --url http://127.0.0.1:54321 --logfile cloudflared.log >/dev/null 2>&1 &)

for _ in $(seq 1 30); do
    CF_ENDPOINT=$(grep -oP -m 1 'https://[-.\w]+\.trycloudflare\.com' cloudflared.log | tail -n1)
    if [ -n "${CF_ENDPOINT}" ]; then
        echo "chisel client --keepalive 30s --auth chisel:chisel $CF_ENDPOINT 6065:socks"
        break
    fi
    sleep 1
done
