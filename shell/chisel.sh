#!/bin/sh

# wget -q -O - https://t.cn/A6PelRzV | sh
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/chisel.sh | sh

export PATH="$PATH:."
export WORK_DIR="/tmp"

cd $WORK_DIR

if [ ! -x $WORK_DIR/chisel ]; then
    wget -q -O chisel.gz https://github.com/jpillora/chisel/releases/download/1.3.0/chisel_linux_amd64.gz
    gzip -d chisel.gz && chmod +x chisel
fi

if [ ! -x $WORK_DIR/cloudflared ]; then
    wget -q -O cloudflared.tgz https://bin.equinox.io/c/VdrWdbjqyF/cloudflared-stable-linux-amd64.tgz
    tar xf cloudflared.tgz
fi

pkill -x chisel
pkill -x cloudflared
truncate -s 0 $WORK_DIR/cloudflared.log
(chisel server --host 127.0.0.1 --port 54321 --auth chisel:chisel --socks5 >/dev/null 2>&1 &)
(cloudflared tunnel --no-autoupdate --url http://127.0.0.1:54321 --logfile $WORK_DIR/cloudflared.log >/dev/null 2>&1 &)
