#!/bin/bash

# wget -q -O - https://jihulab.com/RandomK/scripts/raw/master/shell/iprules.sh | bash -s eth0

if [[ "$(whoami)" != "root" ]]; then
    echo "Please run script as root!"
    exit 1
fi

if [ ! -x "$(command -v ipset)" ]; then
    echo "ipset is not installed!"
    exit 1
fi

if [[ -n "$1" ]]; then
    interface=$1
else
    interface=$(ip -4 -o addr show scope global | awk '/(eth[0-9]|en[0-9a-z]+)/ {print $2}' | head -n1)
fi

ip addr show $interface >/dev/null 2>&1
if [[ $? -ne 0 ]]; then
    echo "interface: [$interface] is invalid!"
    exit 1
fi

iptables -F FIREWALL 2>/dev/null
iptables -N FIREWALL 2>/dev/null

ipset destroy blacklist 2>/dev/null
ipset destroy whitelist 2>/dev/null
ipset create blacklist hash:net maxelem 65536 timeout 0 2>/dev/null
ipset create whitelist hash:net maxelem 65536 timeout 0 2>/dev/null

iptables -A FIREWALL -i lo -j ACCEPT
iptables -A FIREWALL -i $interface -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FIREWALL -i $interface -m set --match-set whitelist src -j ACCEPT
iptables -A FIREWALL -i $interface -m set --match-set blacklist src -p tcp -j REJECT --reject-with tcp-reset
iptables -A FIREWALL -i $interface -m set --match-set blacklist src -p udp -j REJECT --reject-with icmp-port-unreachable
iptables -A FIREWALL -i $interface -m set --match-set blacklist src -j DROP
iptables -A FIREWALL -j RETURN

iptables -D INPUT -j FIREWALL 2>/dev/null
iptables -I INPUT -j FIREWALL

iptables -D FORWARD -j FIREWALL 2>/dev/null
iptables -I FORWARD -j FIREWALL
