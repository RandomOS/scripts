#!/bin/sh

# wget -q -O - https://randomk.coding.net/p/misc/d/scripts/git/raw/master/shell/alpine-init.sh | sh

sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories
apk update && apk add --no-cache bash bash-completion curl vim tzdata

curl -4sk -o /etc/inputrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/etc/inputrc
curl -4sk -o /root/.bashrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.bashrc
curl -4sk -o /root/.vimrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.vimrc
