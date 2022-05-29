#!/bin/sh

# wget -q -O - https://randomk.coding.net/p/misc/d/scripts/git/raw/master/shell/alpine-lab.sh | bash -s alpine-lab
# wget -q -O - https://randomk.coding.net/p/misc/d/scripts/git/raw/master/shell/alpine-lab.sh | sh

grep -qs docker /proc/self/cgroup

if [ $? -ne 0 ]; then
    if [ -x "$(command -v docker)" ]; then
        container_name="alpine-lab"
        image_name="randomos/alpine-lab"

        [ -n "$1" ] && container_name="$1"

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            docker rm -f $container_name
        fi

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            docker create -it --hostname "$container_name" --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -v /dev/shm:/dev/shm \
                --init \
                $image_name /bin/sh
            docker start $container_name
        fi
    fi
    exit
fi
