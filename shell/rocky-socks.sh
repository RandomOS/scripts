#!/bin/sh

# wget -q -O - https://code.aliyun.com/RandomK/scripts/raw/master/shell/rocky-socks.sh | bash -s rocky-socks 3721 helloworld
# wget -q -O - https://code.aliyun.com/RandomK/scripts/raw/master/shell/rocky-socks.sh | sh

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

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            docker rm -f $container_name
        fi

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            docker create -it --net host --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -e ENCRYPT_KEY=$encrypt_key \
                -e PORT=$exposed_port \
                -v /dev/shm:/dev/shm \
                --restart unless-stopped \
                --init \
                $image_name /run.sh
            wget -q -O /tmp/run.sh https://code.aliyun.com/RandomK/scripts/raw/master/shell/rocky-socks.sh \
                && chmod +x /tmp/run.sh \
                && docker cp /tmp/run.sh $container_name:/run.sh \
                && rm -f /tmp/run.sh \
                && docker start $container_name
        fi
    fi
    exit
fi

if [ ! -x "$(command -v socks)" ]; then
    wget -q -O /bin/socks.gz http://rocky.evai.pl/ftp/bin/linux/amd64/socks.gz \
        && gzip -d /bin/socks.gz \
        && chmod +x /bin/socks
fi

if [ ! -x "$(command -v pytunnel)" ]; then
    wget -q -O /bin/pytunnel https://randomk.coding.net/p/misc/d/scripts/git/raw/master/python/pytunnel_async.py \
        && chmod +x /bin/pytunnel
fi

socks -d -i127.0.0.1 -p51080
pytunnel -m server -l 0.0.0.0:$PORT -r 127.0.0.1:51080 -k $ENCRYPT_KEY
