#!/bin/sh

# wget -q -O - http://t.cn/A6zKRKsu | sh
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/install-docker.sh | sh

if [ "$(whoami)" != "root" ]; then
    exit
fi

if [ -x "$(command -v docker)" ]; then
    echo "docker already installed"
    exit
fi

curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun

mkdir -p /etc/docker
cat << EOF > /etc/docker/daemon.json
{
    "registry-mirrors": ["https://hub-mirror.c.163.com"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "1m",
        "max-file": "1"
    }
}
EOF

service docker restart
