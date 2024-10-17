#!/bin/sh

# wget -q -O - https://cdn.randomk.org/scripts/shell/install-docker.sh | sh

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
    "registry-mirrors": ["https://docker.mxdyeah.top"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "1m",
        "max-file": "1"
    }
}
EOF

service docker restart
