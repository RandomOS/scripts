#!/bin/bash

# curl -fsSL https://raw.githubusercontent.com/RandomOS/scripts/master/shell/install_docker.sh | bash

if [[ $(whoami) != "root" ]]; then
    exit
fi

if [[ -x $(command -v docker) ]]; then
    echo "docker already installed"
    exit
fi

curl -fsSL https://www.qualcomm.cn/cdn-cgi/trace | grep -wq 'loc=CN'
if [[ $? -eq 0 ]]; then
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
else
    curl -fsSL https://get.docker.com | bash -s docker
fi

mkdir -p /etc/docker
cat <<EOF >/etc/docker/daemon.json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "1m",
        "max-file": "1"
    },
    "live-restore": true
}
EOF

service docker restart
