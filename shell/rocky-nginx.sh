#!/bin/sh

# wget -q -O - https://url.cn/5ypyM09 | bash -s rocky-nginx
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/rocky-nginx.sh | sh

grep -qs docker /proc/self/cgroup

if [ $? -ne 0 ]; then
    if [ -x "$(command -v docker)" ]; then
        container_name="rocky-nginx"
        image_name="alpine:3.10"

        [ -n "$1" ] && container_name="$1"

        if [ -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker rm -f $container_name
        fi

        if [ ! -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker create -it --net host --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -v /run/shm:/run/shm \
                $image_name /run.sh
            wget -q -O /tmp/run.sh https://url.cn/5ypyM09 && chmod +x /tmp/run.sh
            docker cp /tmp/run.sh $container_name:/run.sh && rm /tmp/run.sh
            docker start $container_name
        fi
    fi
    exit
fi

mkdir -p /etc/nginx
mkdir -p /var/log/nginx
mkdir -p /var/lib/nginx/body
mkdir -p /var/lib/nginx/fastcgi
mkdir -p /var/lib/nginx/proxy
mkdir -p /var/lib/nginx/scgi
mkdir -p /var/lib/nginx/uwsgi

if [ ! -x "$(command -v nginx)" ]; then
    wget -q -O /usr/sbin/nginx.gz https://r.mipcdn.com/c/s/geocities.ws/rocky/bin/linux/amd64/nginx.gz && gzip -d /usr/sbin/nginx.gz && chmod +x /usr/sbin/nginx
fi

if [ ! -f /etc/nginx/nginx.conf ]; then
    wget -q -O /etc/nginx/nginx.conf https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/rocky-nginx/etc/nginx/nginx.conf
fi

nginx -g 'daemon off;'
