#!/bin/sh

# wget -q -O - https://jihulab.com/RandomK/scripts/raw/master/shell/alpine-lab.sh | bash -s alpine-lab
# wget -q -O - https://jihulab.com/RandomK/scripts/raw/master/shell/alpine-lab.sh | sh

if [ ! -x "$(command -v docker)" ]; then
    echo "docker is not installed"
    exit 1
fi

container_name="alpine-lab"
image_name="randomos/alpine-lab"

[ -n "$1" ] && container_name="$1"

docker container inspect $container_name >/dev/null 2>&1
if [ $? -eq 0 ]; then
    docker rm -f $container_name
fi

docker container inspect $container_name >/dev/null 2>&1
if [ $? -ne 0 ]; then
    docker run -d --hostname "$container_name" --name "$container_name" \
        -e TZ=Asia/Shanghai \
        -v /dev/shm:/dev/shm \
        -w /root \
        --init \
        $image_name tail -f /dev/null
fi
