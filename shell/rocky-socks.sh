#!/bin/sh

# wget -q -O - https://t.cn/A6wi8KeU | bash -s rocky-socks 3721 helloworld
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/rocky-socks.sh | sh

grep -qs docker /proc/self/cgroup

if [ $? -ne 0 ]; then
    if [ -x "$(command -v docker)" ]; then
        container_name="rocky-socks"
        image_name="randomos/staticpython"
        exposed_port="3721"
        encrypt_key="helloworld"

        [ -n "$1" ] && container_name="$1"
        [ -n "$2" ] && exposed_port="$2"
        [ -n "$3" ] && encrypt_key="$3"

        if [ -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker rm -f $container_name
        fi

        if [ ! -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker create -it --hostname "$container_name" --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -e ENCRYPT_KEY=$encrypt_key \
                -v /run/shm:/run/shm \
                -p $exposed_port:3721 \
                --restart unless-stopped \
                $image_name /run.sh
            wget -q -O /tmp/run.sh https://t.cn/A6wi8KeU \
                && chmod +x /tmp/run.sh \
                && docker cp /tmp/run.sh $container_name:/run.sh \
                && rm /tmp/run.sh \
                && docker start $container_name
        fi
    fi
    exit
fi

if [ ! -x "$(command -v socks)" ]; then
    wget -q -O /bin/socks.gz https://geocities.ws/rocky/bin/linux/amd64/socks.gz \
        && gzip -d /bin/socks.gz \
        && chmod +x /bin/socks
fi

if [ ! -x "$(command -v pytunnel)" ]; then
    wget -q -O /bin/pytunnel https://gitee.com/randomk/scripts/raw/master/python/pytunnel_async.py \
        && chmod +x /bin/pytunnel
fi

socks -d -i127.0.0.1 -p1080
pytunnel -m server -l 0.0.0.0:3721 -r 127.0.0.1:1080 -k $ENCRYPT_KEY
