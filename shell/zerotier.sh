#!/bin/sh

# wget -q -O - https://jihulab.com/RandomK/scripts/raw/master/shell/zerotier.sh | sh

if [ ! -x "$(command -v docker)" ]; then
    echo "docker is not installed"
    exit 1
fi

container_name="zerotier-one"

docker container inspect $container_name >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "$container_name already exists"
    exit 1
fi

docker create -it --hostname $container_name --name $container_name \
    -e TZ=Asia/Shanghai \
    --cap-add NET_ADMIN \
    --device /dev/net/tun \
    -v /dev/shm:/dev/shm \
    -v zerotier-storage:/var/lib/zerotier-one \
    --restart unless-stopped \
    --entrypoint /run.sh \
    zerotier/zerotier:1.12.2

cat << 'EOF' > /tmp/run.sh
#!/bin/sh

cp /etc/apt/sources.list /etc/apt/sources.list.orig
sed -i '/snapshot.debian.org/d' /etc/apt/sources.list
sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

apt-get update
apt-get install -y curl vim tzdata procps net-tools iproute2 iputils-ping netcat-openbsd
apt-get clean

curl -4sk -m 5 -o /root/.bashrc https://fastly.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.bashrc
curl -4sk -m 5 -o /root/.vimrc https://fastly.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.vimrc

if [ "$(arch)" = "x86_64" ]; then
    arch="amd64"
elif [ "$(arch)" = "aarch64" ]; then
    arch="arm7"
elif [ "$(arch)" = "armv7l" ]; then
    arch="arm7"
fi

if [ -n "${arch}" ]; then
    curl -4sk -m 30 -o /usr/local/bin/tcppm.gz https://rocky.randomk.xyz/ftp/bin/linux/${arch}/tcppm.gz \
        && gzip -d /usr/local/bin/tcppm.gz \
        && chmod +x /usr/local/bin/tcppm

    curl -4sk -m 30 -o /usr/local/bin/socks.gz https://rocky.randomk.xyz/ftp/bin/linux/${arch}/socks.gz \
        && gzip -d /usr/local/bin/socks.gz \
        && chmod +x /usr/local/bin/socks
fi

echo '#!/bin/sh' > /run.sh
echo '' >> /run.sh
echo 'exec /entrypoint.sh' >> /run.sh
EOF

chmod +x /tmp/run.sh \
    && docker cp /tmp/run.sh $container_name:/run.sh \
    && docker start zerotier-one \
    && rm -f /tmp/run.sh
