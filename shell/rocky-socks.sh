#!/bin/sh

# wget -q -O - https://gitlab.com/RandomK/scripts/raw/master/shell/rocky-socks.sh | bash -s rocky-socks 3721 helloworld
# wget -q -O - https://gitlab.com/RandomK/scripts/raw/master/shell/rocky-socks.sh | sh

container_name="rocky-socks"
exposed_port="3721"
encrypt_key="helloworld"

[ -n "$1" ] && container_name="$1"
[ -n "$2" ] && exposed_port="$2"
[ -n "$3" ] && encrypt_key="$3"

docker run -d --net host --name $container_name \
    -e ENCRYPT_KEY=$encrypt_key \
    -e PORT=$exposed_port \
    -v /dev/shm:/dev/shm \
    --restart unless-stopped \
    --init \
    randomos/rocky-socks
