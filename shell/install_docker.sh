#!/bin/sh

# wget -q -O - https://gitlab.com/RandomK/scripts/raw/master/shell/install_docker.sh | sh

if [ "$(whoami)" != "root" ]; then
    exit
fi

if [ -x "$(command -v docker)" ]; then
    echo "docker already installed"
    exit
fi

curl -fsSL https://get.docker.com | bash -s docker --mirror AzureChinaCloud

mkdir -p /etc/docker
cat << EOF > /etc/docker/daemon.json
{
    "registry-mirrors": [
        "https://hub.fast360.xyz"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "1m",
        "max-file": "1"
    },
    "live-restore": true
}
EOF

service docker restart
