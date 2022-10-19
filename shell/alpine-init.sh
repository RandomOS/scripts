#!/bin/sh

# wget -q -O - https://jihulab.com/RandomK/scripts/raw/master/shell/alpine-init.sh | sh

sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories
apk update && apk add --no-cache bash bash-completion curl vim tzdata

curl -4sk -o /etc/inputrc https://fastly.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/etc/inputrc
curl -4sk -o /root/.bashrc https://fastly.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.bashrc
curl -4sk -o /root/.vimrc https://fastly.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.vimrc
