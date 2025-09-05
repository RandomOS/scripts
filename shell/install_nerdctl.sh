#!/bin/bash

# wget -q -O - https://gitlab.com/RandomK/scripts/raw/master/shell/install_nerdctl.sh | bash

NERDCTL_VERSION="2.1.4"

if [[ $(whoami) != "root" ]]; then
    exit
fi

if [[ -x $(command -v nerdctl) ]]; then
    echo "nerdctl already installed"
    exit
fi

rm -rf /tmp/install \
    && mkdir -p /tmp/install \
    && cd /tmp/install \
    && wget -q -O data.tar.gz https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-full-${NERDCTL_VERSION}-linux-amd64.tar.gz \
    && tar -C /usr/local -xf data.tar.gz \
    && ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker \
    && cd /tmp \
    && rm -rf /tmp/install

if [[ $? -ne 0 ]]; then
    echo "[error] download failed"
    exit
fi

systemctl enable --now containerd

modprobe overlay
modprobe br_netfilter

cat <<EOF >/etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF

cat <<EOF >/etc/sysctl.d/99-containerd.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sysctl --system >/dev/null 2>&1

# set registry mirror
mkdir -p /etc/containerd
cat <<'EOF' >/etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
EOF

mkdir -p /etc/containerd/certs.d/docker.io
cat <<'EOF' >/etc/containerd/certs.d/docker.io/hosts.toml
server = "https://docker.io"

[host."https://docker.1ms.run"]
  capabilities = ["pull", "resolve"]
EOF

systemctl restart containerd
