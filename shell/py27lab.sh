#!/bin/sh

# curl -fsSL https://gitlab.com/RandomK/scripts/raw/master/shell/py27lab.sh | bash -s py27-lab
# wget -q -O - https://gitlab.com/RandomK/scripts/raw/master/shell/py27lab.sh | bash -s py27-lab

cat << 'EOF' > /tmp/run.sh
cp /etc/apt/sources.list /etc/apt/sources.list.orig
sed -i '/snapshot.debian.org/d' /etc/apt/sources.list
sed -i 's/deb.debian.org/mirrors.huaweicloud.com/g' /etc/apt/sources.list
sed -i 's/security.debian.org/mirrors.huaweicloud.com/g' /etc/apt/sources.list

apt-get update && apt-get install -y bash bash-completion curl vim tzdata

mkdir -p /root/.pip
curl -4sk -m 5 -o /root/.pip/pip.conf https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.pip/pip.conf
curl -4sk -m 5 -o /root/.bashrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.bashrc
curl -4sk -m 5 -o /root/.vimrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.vimrc

pip install -qq --no-cache-dir --upgrade pip
pip install -qq --no-cache-dir ipython==3.2.3
EOF

container_name="py27-lab"
image_name="python:2.7-buster"

[ -n "$1" ] && container_name="$1"

docker container inspect $container_name >/dev/null 2>&1
if [ $? -eq 0 ]; then
    docker rm -f $container_name
fi

docker container inspect $container_name >/dev/null 2>&1
if [ $? -ne 0 ]; then
    docker run -d --net host --name "$container_name" \
        -e TZ=Asia/Shanghai \
        -v /dev/shm:/dev/shm \
        -w /root \
        --init \
        $image_name tail -f /dev/null
    docker cp /tmp/run.sh $container_name:/tmp/run.sh
    docker exec $container_name sh /tmp/run.sh
fi
