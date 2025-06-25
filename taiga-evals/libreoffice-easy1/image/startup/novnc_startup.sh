#!/bin/bash
echo "starting noVNC"

# Start noVNC with explicit websocket settings
/workdir/noVNC/utils/novnc_proxy \
    --vnc localhost:5900 \
    --listen 6080 \
    --web /workdir/noVNC \
    > /tmp/novnc.log 2>&1 &

# Wait for noVNC to start
timeout=10
while [ $timeout -gt 0 ]; do
    if netstat -tuln | grep -q ":6080 "; then
        break
    fi
    sleep 1
    timeout=$((timeout-1))
done

echo "noVNC started successfully"
