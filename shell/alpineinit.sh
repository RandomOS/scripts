#!/bin/bash

# wget -q -O - https://gitlab.com/RandomK/scripts/raw/master/shell/alpineinit.sh | bash

wget -q -O - https://www.qualcomm.cn/cdn-cgi/trace | grep -wq 'loc=CN'
[ $? -eq 0 ] && sed -i 's/dl-cdn.alpinelinux.org/mirrors.huaweicloud.com/g' /etc/apk/repositories

apk update && apk add --no-cache bash bash-completion curl vim tzdata

curl -4sk -m 5 -o /etc/inputrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/etc/inputrc
curl -4sk -m 5 -o /root/.bashrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.bashrc
curl -4sk -m 5 -o /root/.vimrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.vimrc
