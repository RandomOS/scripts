#!/bin/sh

# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/alpine-arm.sh | sh

if [ ! -x "$(command -v docker)" ]; then
    echo "docker is not installed"
    exit 1
fi

docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

docker rm -f alpine-arm >/dev/null 2>&1
docker create -it --hostname "alpine-arm" --name "alpine-arm" \
    -e TZ=Asia/Shanghai \
    -v /run/shm:/run/shm \
    --init \
    multiarch/alpine:armhf-v3.10 /bin/sh
docker start alpine-arm

docker rm -f alpine-arm64 >/dev/null 2>&1
docker create -it --hostname "alpine-arm64" --name "alpine-arm64" \
    -e TZ=Asia/Shanghai \
    -v /run/shm:/run/shm \
    --init \
    multiarch/alpine:arm64-v3.10 /bin/sh
docker start alpine-arm64
