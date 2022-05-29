#!/bin/sh

# wget -q -O - https://randomk.coding.net/p/misc/d/scripts/git/raw/master/shell/bionic-lab.sh | bash -s bionic-lab
# wget -q -O - https://randomk.coding.net/p/misc/d/scripts/git/raw/master/shell/bionic-lab.sh | sh

grep -qs docker /proc/self/cgroup

if [ $? -ne 0 ]; then
    if [ -x "$(command -v docker)" ]; then
        container_name="bionic-lab"
        image_name="ubuntu:bionic"

        [ -n "$1" ] && container_name="$1"

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            docker rm -f $container_name
        fi

        docker container inspect $container_name >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            docker create -it --net host --name "$container_name" \
                -e TZ=Asia/Shanghai \
                -e LANG=en_US.UTF-8 \
                -v /dev/shm:/dev/shm \
                $image_name /bin/sh
            wget -q -O /tmp/run.sh https://randomk.coding.net/p/misc/d/scripts/git/raw/master/shell/bionic-lab.sh \
                && docker cp /tmp/run.sh $container_name:/tmp/run.sh \
                && rm -f /tmp/run.sh \
                && docker start $container_name \
                && docker exec $container_name sh /tmp/run.sh
        fi
    fi
    exit
fi

sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list

apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y bash bash-completion curl wget vim locales tzdata \
    && apt-get clean \
    && locale-gen en_US.UTF-8 \
    && echo $TZ > /etc/timezone \
    && ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata

mkdir -p /root/.pip
curl -4sk -o /root/.pip/pip.conf https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.pip/pip.conf
curl -4sk -o /root/.bashrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/ubuntu-bionic/root/.bashrc
curl -4sk -o /root/.vimrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/ubuntu-bionic/root/.vimrc
