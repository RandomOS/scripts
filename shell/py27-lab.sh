#!/bin/sh

# wget -q -O - https://url.cn/5bB24iM | sh
# wget -q -O - https://gitee.com/randomk/scripts/raw/master/shell/py27-lab.sh | sh

grep -qs docker /proc/self/cgroup

if [ $? -ne 0 ]; then
    if [ -x "$(command -v docker)" ]; then
        container_name="py27-lab"
        image_name="python:2.7-buster"

        if [ -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker rm -f $container_name
        fi

        if [ ! -n "$(docker ps -aq -f name=$container_name)" ]; then
            docker create -it --net host --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -v /run/shm:/run/shm \
                $image_name /bin/sh
            docker start $container_name
            docker exec $container_name wget -q -O /tmp/run.sh https://url.cn/5bB24iM
            docker exec $container_name sh /tmp/run.sh
        fi
    fi
    exit
fi

mkdir -p /root/.pip

cat <<EOF >/root/.pip/pip.conf
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
disable-pip-version-check = true
format = columns
EOF

pip install -qq --no-cache-dir pip==18.1 ipython==3.2.3

sed -i '/snapshot.debian.org/d' /etc/apt/sources.list
sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

apt update && apt-get install -y bash bash-completion curl vim tzdata

curl -4sk -o /root/.bashrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.bashrc
curl -4sk -o /root/.vimrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.vimrc
