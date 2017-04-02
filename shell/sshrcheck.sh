#!/bin/sh

nc -nvz 192.168.0.110 2222 && nc -nvz 192.168.0.110 3389
if [ $? -ne 0 ]; then
    pgrep -u pi -x -a sshd | awk '$3=="pi" {print $1}' | xargs -r kill
fi
