#!/bin/sh

# wget -q -O - https://t.cn/A6PelRzV | sh
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/chisel.sh | sh

PATH="$PATH:."
WORK_DIR="/tmp/chisel"

CHISEL_VERSION="1.4.0"

mkdir -p $WORK_DIR && cd $WORK_DIR

if [ ! -x $WORK_DIR/chisel ]; then
    wget -q -O chisel.gz https://github.com/jpillora/chisel/releases/download/v${CHISEL_VERSION}/chisel_${CHISEL_VERSION}_linux_amd64.gz \
        && gzip -d chisel.gz \
        && chmod +x chisel
fi

if [ ! -x $WORK_DIR/cloudflared ]; then
    wget -q -O cloudflared.tgz https://bin.equinox.io/c/VdrWdbjqyF/cloudflared-stable-linux-amd64.tgz \
        && tar xf cloudflared.tgz \
        && rm -f cloudflared.tgz
fi

truncate -s 0 cloudflared.log

pkill -x chisel
pkill -x cloudflared
(chisel server --host 127.0.0.1 --port 54321 --auth chisel:chisel --socks5 >/dev/null 2>&1 &)
(cloudflared tunnel --no-autoupdate --url http://127.0.0.1:54321 --logfile cloudflared.log >/dev/null 2>&1 &)

while true; do
    CF_ENDPOINT=$(grep -P -o -m 1 'https://[-.\w]+\.trycloudflare\.com' cloudflared.log)
    if [ $? -eq 0 ]; then
        echo "chisel client --keepalive 30s --auth chisel:chisel $CF_ENDPOINT 7070:socks"
        break
    fi
    sleep 1
done
