#!/bin/sh

# Create new chain
iptables -t nat -N SHADOWSOCKS

# Ignore your shadowsocks server's addresses
iptables -t nat -A SHADOWSOCKS -d 30.0.0.0 -j RETURN

# Ignore LANs IP address
iptables -t nat -A SHADOWSOCKS -d 0.0.0.0/8 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 10.0.0.0/8 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 127.0.0.0/8 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 169.254.0.0/16 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 172.16.0.0/12 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 192.168.0.0/16 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 224.0.0.0/4 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 240.0.0.0/4 -j RETURN

# Ignore China IP address
iptables -t nat -A SHADOWSOCKS -d 123.125.71.38 -j RETURN

# Anything else should be redirected to shadowsocks's local port
iptables -t nat -A SHADOWSOCKS -p tcp -j REDIRECT --to-ports 4096

# Apply the rules for other device
iptables -t nat -A PREROUTING -p tcp -j SHADOWSOCKS

# Apply the rules for device itself
iptables -t nat -A OUTPUT -p tcp -j SHADOWSOCKS
