#!/bin/sh

while true; do
    if [ ! -n "$(pgrep -f 'ssh -qnfNT -R 127.0.0.1:22222:192.168.0.110:22')" ]; then
        ssh -qnfNT -R 127.0.0.1:22222:192.168.0.110:22 \
            -o ServerAliveInterval=15 \
            -o ExitOnForwardFailure=yes \
        root@192.168.0.110
    fi
    sleep 5
done
