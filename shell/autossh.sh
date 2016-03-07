#!/bin/sh

while true; do
    if [ ! -n "$(ps aux | grep qnfNT | grep -v grep)" ]; then
        ssh -qnfNT -R 443:127.0.0.1:22 root@192.168.0.110 -p 22
    fi
    sleep 5
done
