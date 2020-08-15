#!/bin/sh

# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/rocky-nginx.sh | bash -s rocky-nginx
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/rocky-nginx.sh | sh

grep -qs docker /proc/self/cgroup

if [ $? -ne 0 ]; then
    if [ -x "$(command -v docker)" ]; then
        container_name="rocky-nginx"
        image_name="alpine:3.10"

        [ -n "$1" ] && container_name="$1"

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            docker rm -f $container_name
        fi

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            docker create -it --net host --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -v /run/shm:/run/shm \
                --restart unless-stopped \
                $image_name nginx -g 'daemon off;'
            wget -q -O /tmp/run.sh https://gitee.com/randomk/scripts/raw/master/shell/rocky-nginx.sh \
                && chmod +x /tmp/run.sh \
                && docker cp /tmp/run.sh $container_name:/usr/sbin/nginx \
                && rm -f /tmp/run.sh \
                && docker start $container_name
        fi
    fi
    exit
fi

sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

apk update && apk --no-cache add tzdata

mkdir -p /etc/nginx
mkdir -p /var/log/nginx
mkdir -p /var/lib/nginx/body
mkdir -p /var/lib/nginx/fastcgi
mkdir -p /var/lib/nginx/proxy
mkdir -p /var/lib/nginx/scgi
mkdir -p /var/lib/nginx/uwsgi

wget -q -O /etc/nginx/nginx.conf https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/rocky-nginx/etc/nginx/nginx.conf
wget -q -O /usr/sbin/nginx.gz https://geocities.ws/rocky/bin/linux/amd64/alpine/nginx.gz && gzip -df /usr/sbin/nginx.gz && chmod +x /usr/sbin/nginx
