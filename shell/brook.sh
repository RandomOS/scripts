#!/bin/sh

# wget -q -O - https://code.aliyun.com/RandomK/scripts/raw/master/shell/brook.sh | sh

BROOK_VERSION="20220707"

PATH="$PATH:."
WORK_DIR="/tmp/brook"

mkdir -p $WORK_DIR && cd $WORK_DIR

if [ ! -x $WORK_DIR/brook ]; then
    wget -q -O brook https://github.com/txthinking/brook/releases/download/v${BROOK_VERSION}/brook_linux_amd64 \
        && chmod +x brook
fi

if [ ! -x $WORK_DIR/cloudflared ]; then
    wget -q -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
        && chmod +x cloudflared
fi

truncate -s 0 cloudflared.log

pkill -x brook
pkill -x cloudflared
(brook wsserver -l 127.0.0.1:54321 -p brook --path /brook/ >/dev/null 2>&1 &)
(cloudflared tunnel --no-autoupdate --url http://127.0.0.1:54321 --logfile cloudflared.log >/dev/null 2>&1 &)

for _ in `seq 1 30`; do
    CF_ENDPOINT=$(grep -oP -m 1 'https://[-.\w]+\.trycloudflare\.com' cloudflared.log)
    if [ $? -eq 0 ]; then
        BROOK_ENDPOINT=$(echo ${CF_ENDPOINT} | sed 's|https:|wss:|')
        echo "brook wsclient -s ${BROOK_ENDPOINT}/brook/ -p brook --socks5 0.0.0.0:6065"
        break
    fi
    sleep 1
done
