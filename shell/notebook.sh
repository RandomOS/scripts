#!/bin/bash

# curl -fsSL https://raw.githubusercontent.com/RandomOS/scripts/master/shell/notebook.sh | bash -s notebook
# wget -q -O - https://raw.githubusercontent.com/RandomOS/scripts/master/shell/notebook.sh | bash -s notebook

cat <<'EOE' >/tmp/run.sh
mkdir -p ~/.pip
cat <<'EOF' > ~/.pip/pip.conf
[global]
index-url = https://mirrors.aliyun.com/pypi/simple
trusted-host = mirrors.aliyun.com
disable-pip-version-check = true
format = columns
EOF

PASSWORD=$(python -c "from jupyter_server.auth import passwd; print(passwd('123456'))")
cat <<EOF > ~/.jupyter/jupyter_server_config.json
{
    "IdentityProvider": {
        "hashed_password": "${PASSWORD}"
    }
}
EOF

sudo sed -i -e 's|archive.ubuntu.com|mirrors.huaweicloud.com|' -e 's|security.ubuntu.com|mirrors.huaweicloud.com|' /etc/apt/sources.list.d/ubuntu.sources
# sudo apt-get update -qq
# sudo apt-get install -y iproute2 >/dev/null 2>&1

pip install pipdeptree >/dev/null 2>&1
EOE

container_name="notebook"
image_name="quay.io/jupyter/scipy-notebook:python-3.13"

[[ -n $1 ]] && container_name="$1"

docker container inspect $container_name >/dev/null 2>&1
if [[ $? -eq 0 ]]; then
    docker rm -f $container_name
fi

docker container inspect $container_name >/dev/null 2>&1
if [[ $? -ne 0 ]]; then
    docker run -d --net host --name "$container_name" \
        -e TZ=Asia/Shanghai \
        -e GRANT_SUDO=yes \
        -e RESTARTABLE=yes \
        -e DOCKER_STACKS_JUPYTER_CMD=notebook \
        -v /dev/shm:/dev/shm \
        --user root \
        --restart unless-stopped \
        quay.io/jupyter/scipy-notebook:python-3.13
    docker cp /tmp/run.sh $container_name:/tmp/run.sh
    docker exec $container_name sudo -u jovyan bash /tmp/run.sh
    docker restart -t 1 $container_name
fi
