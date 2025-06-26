#!/bin/bash
set -e  # Exit on error

# Function to check if tint2 is already running
check_tint2_running() {
    if xdotool search --class "tint2" >/dev/null 2>&1; then
        return 0  # tint2 is already running
    else
        return 1  # tint2 is not running
    fi
}

# Check if tint2 is already running
if check_tint2_running; then
    exit 0
fi

# Start tint2 and capture its stderr
tint2 -c ${WORKDIR}/image/.config/tint2/tint2rc 2>/tmp/tint2_stderr.log &

# Wait for tint2 window properties to appear
timeout=30
while [ $timeout -gt 0 ]; do
    if check_tint2_running; then
        break
    fi
    sleep 1
    timeout=$((timeout-1))
done

if [ $timeout -eq 0 ]; then
    echo "tint2 stderr output:" >&2
    cat /tmp/tint2_stderr.log >&2
    exit 1
fi

# Remove the temporary stderr log file
rm /tmp/tint2_stderr.log
