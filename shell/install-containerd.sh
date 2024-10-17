#!/bin/shhttps://ghp.ci

# wget -q -O - https://cdn.randomk.org/scripts/shell/install-containerd.sh | sh

CONTAINERD_VERSION="1.7.22"
NERDCTL_VERSION="1.7.7"
RUNC_VERSION="1.1.15"
CNI_VERSION="1.5.1"

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
    && wget -q -O data.tar.gz https://ghp.ci/https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz \
    && tar -C /usr/local -xf data.tar.gz \
    && wget -q -O data.tar.gz https://ghp.ci/https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-${NERDCTL_VERSION}-linux-amd64.tar.gz \
    && tar -C /usr/local/bin -xf data.tar.gz \
    && ln -sf /usr/local/bin/nerdctl /usr/local/bin/docker \
    && wget -q -O runc.amd64 https://ghp.ci/https://github.com/opencontainers/runc/releases/download/v${RUNC_VERSION}/runc.amd64 \
    && install -m 755 runc.amd64 /usr/local/sbin/runc \
    && mkdir -p /opt/cni/bin \
    && wget -q -O data.tar.gz https://ghp.ci/https://github.com/containernetworking/plugins/releases/download/v${CNI_VERSION}/cni-plugins-linux-amd64-v${CNI_VERSION}.tgz \
    && tar -C /opt/cni/bin -xf data.tar.gz \
    && mkdir -p /usr/local/lib/systemd/system \
    && wget -q -O /usr/local/lib/systemd/system/containerd.service https://ghp.ci/https://raw.githubusercontent.com/containerd/containerd/main/containerd.service \
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

[host."https://docker.mxdyeah.top"]
  capabilities = ["pull", "resolve"]
EOF

systemctl restart containerd
