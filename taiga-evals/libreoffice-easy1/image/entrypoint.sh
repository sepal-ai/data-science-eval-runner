#!/bin/bash

set -e

# Set up the display
export DISPLAY=:${DISPLAY_NUM}


########################################################################################################################
## MCP reacts poorly to debug output from the container
## but when debugging it's helpful to see container output, particularly
## during startup. So you can run like the following to print (and remove `VERBOSE=1` in claude_desktop_config.json)
## docker run -e VERBOSE=1 -e WIDTH=1024 -e HEIGHT=768 taiga uv --directory /mcp_server run tail -f /dev/null
########################################################################################################################
VERBOSE=${VERBOSE:-0}

# Function to execute commands with or without redirection based on verbosity setting
run_command() {
  local cmd="$1"

  if [ "$VERBOSE" -eq 0 ]; then
    # Silent mode - redirect to /dev/null
    eval "$cmd > /dev/null 2>&1"
  else
    # Verbose mode - no redirection
    eval "$cmd"
  fi
}

#########################################################################################################
## Running all UI related startup scripts as `model`
#########################################################################################################

# tint2 can be a flake, try up to 3 times
for attempt in {1..3}; do
  if run_command "su model -c ${WORKDIR}/image/startup/xvfb_startup.sh" && run_command "su model -c ${WORKDIR}/image/startup/tint2_startup.sh"; then
    break
  fi

  if [ "$attempt" -eq 3 ]; then
    echo "Failed to start xvfb/tint2 after 3 attempts." >&2
    exit 1
  fi

  sleep 2
done

run_command "su model -c ${WORKDIR}/image/startup/mutter_startup.sh"
run_command "su model -c ${WORKDIR}/image/startup/x11vnc_startup.sh"
run_command "su model -c ${WORKDIR}/image/startup/novnc_startup.sh"
### END: Run startup scripts

run_command "libreoffice --calc" &
