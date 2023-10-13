#!/bin/sh

# wget -q -O - https://jihulab.com/RandomK/scripts/raw/master/shell/install-containerd.sh | sh

if [ "$(whoami)" != "root" ]; then
    exit
fi

if [ -x "$(command -v containerd)" ]; then
    echo "containerd already installed"
    exit
fi

rm -rf /tmp/install \
    && mkdir -p /tmp/install \
    && cd /tmp/install \
    && wget -q -O data.tar.gz https://ghproxy.com/https://github.com/containerd/containerd/releases/download/v1.7.5/containerd-1.7.5-linux-amd64.tar.gz \
    && tar -C /usr/local -xf data.tar.gz \
    && wget -q -O data.tar.gz https://ghproxy.com/https://github.com/containerd/nerdctl/releases/download/v1.6.2/nerdctl-1.6.2-linux-amd64.tar.gz \
    && tar -C /usr/local/bin -xf data.tar.gz \
    && ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker \
    && wget -q -O runc.amd64 https://ghproxy.com/https://github.com/opencontainers/runc/releases/download/v1.1.9/runc.amd64 \
    && install -m 755 runc.amd64 /usr/local/sbin/runc \
    && mkdir -p /opt/cni/bin \
    && wget -q -O data.tar.gz https://ghproxy.com/https://github.com/containernetworking/plugins/releases/download/v1.3.0/cni-plugins-linux-amd64-v1.3.0.tgz \
    && tar -C /opt/cni/bin -xf data.tar.gz \
    && mkdir -p /usr/local/lib/systemd/system \
    && wget -q -O /usr/local/lib/systemd/system/containerd.service https://ghproxy.com/https://raw.githubusercontent.com/containerd/containerd/main/containerd.service \
    && cd /tmp \
    && rm -rf /tmp/install

if [ $? -ne 0 ]; then
    echo "[error] download failed"
    exit
fi

systemctl enable --now containerd

modprobe overlay
modprobe br_netfilter

cat << EOF > /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF

cat << EOF > /etc/sysctl.d/99-containerd.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sysctl --system >/dev/null 2>&1

# set registry mirror
mkdir -p /etc/containerd
cat << 'EOF' > /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
EOF

mkdir -p /etc/containerd/certs.d/docker.io
cat << 'EOF' > /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://docker.io"

[host."https://docker.mirrors.sjtug.sjtu.edu.cn"]
  capabilities = ["pull", "resolve"]
EOF

systemctl restart containerd
