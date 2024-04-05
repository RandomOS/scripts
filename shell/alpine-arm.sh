#!/bin/sh

# wget -q -O - https://gitlab.com/RandomK/scripts/raw/master/shell/alpine-arm.sh | sh

if [ ! -x "$(command -v docker)" ]; then
    echo "docker is not installed"
    exit 1
fi

docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

docker rm -f alpine-arm >/dev/null 2>&1
docker run -d --hostname "alpine-arm" --name "alpine-arm" \
    -e TZ=Asia/Shanghai \
    -v /dev/shm:/dev/shm \
    -w /root \
    --init \
    multiarch/alpine:armhf-v3.12 tail -f /dev/null

docker rm -f alpine-arm64 >/dev/null 2>&1
docker run -d --hostname "alpine-arm64" --name "alpine-arm64" \
    -e TZ=Asia/Shanghai \
    -v /dev/shm:/dev/shm \
    -w /root \
    --init \
    multiarch/alpine:arm64-v3.12 tail -f /dev/null

docker rm -f alpine-amd64 >/dev/null 2>&1
docker run -d --hostname "alpine-amd64" --name "alpine-amd64" \
    -e TZ=Asia/Shanghai \
    -v /dev/shm:/dev/shm \
    -w /root \
    --init \
    multiarch/alpine:amd64-v3.12 tail -f /dev/null
