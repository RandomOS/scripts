#!/bin/sh

# wget -q -O - https://cdn.randomk.org/scripts/shell/compile-lab.sh | bash -s compile-lab
# wget -q -O - https://cdn.randomk.org/scripts/shell/compile-lab.sh | sh

if [ ! -x "$(command -v docker)" ]; then
    echo "docker is not installed"
    exit 1
fi

cat << 'EOF' > /tmp/run.sh
cp /etc/apk/repositories.orig /etc/apk/repositories

apk add --no-cache \
    gcc \
    make \
    musl-dev \
    libucontext-dev \
    linux-headers \
    file
EOF

container_name="compile-lab"
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
    docker cp /tmp/run.sh $container_name:/tmp/run.sh
    docker exec $container_name sh /tmp/run.sh
fi
