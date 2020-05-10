#!/bin/sh

# wget -q -O - https://t.cn/A6AQXMzj | bash -s compile-lab
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/compile-lab.sh | sh

grep -qs docker /proc/self/cgroup

if [ $? -ne 0 ]; then
    if [ -x "$(command -v docker)" ]; then
        container_name="compile-lab"
        image_name="randomos/alpine-lab"

        [ -n "$1" ] && container_name="$1"

        if [ -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker rm -f $container_name
        fi

        if [ ! -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker create -it --net host --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -v /run/shm:/run/shm \
                $image_name /bin/sh
            docker start $container_name
            docker exec $container_name wget -q -O /tmp/run.sh https://t.cn/A6AQXMzj
            docker exec $container_name sh /tmp/run.sh
        fi
    fi
    exit
fi

apk add --no-cache \
    gcc \
    make \
    musl-dev \
    libucontext-dev \
    linux-headers
