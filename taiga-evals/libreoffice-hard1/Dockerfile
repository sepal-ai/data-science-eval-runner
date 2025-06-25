FROM docker.io/ubuntu:22.04

#############################################################
## Reminder:
## The container WILL NOT have internet access at runtime, 
## so anything the environment needs at runtime should be
## downloaded in the Dockerfile
#############################################################

##########################################################
## !!!! Setting up user for the model to use first !!!!!
## This should happen before any packages are installed, to ensure user ID consistency
## The uid needs to be 1000
##########################################################
RUN groupadd -g 1000 model && \
    useradd -m -u 1000 -g 1000 model && \
    gpasswd -d model root || true

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && apt-get clean

# First install software-properties-common to get add-apt-repository
RUN apt-get update && apt-get install -y software-properties-common curl sudo

# Now add the PPAs
RUN add-apt-repository ppa:deadsnakes/ppa
RUN add-apt-repository ppa:mozillateam/ppa

RUN apt-get update && apt-get install -y \
    curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    #############################################################
    ## START: Basic packages for container
    #############################################################
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    wget \
    git \
    #############################################################
    ## UI packages for computer use
    #############################################################
    xvfb \
    xterm \
    ## `xdotool` used for automating UI interactions (e.g., typing)
    xdotool \
    ## `scrot` used for taking screenshots
    scrot \
    ## `imagemagick` also required for taking screenshots
    imagemagick \
    sudo \
    mutter \
    ## VNC installed to make debugging easier, you can view the UI of the docker container from your laptop
    x11vnc \
    ## Tint2 provides a taskbar, you can add applications to the task bar to make them accessible for the model, look at `.config/tint2` for configuration
    tint2 \
    #############################################################
    ## Networking packages for VNC
    #############################################################
    net-tools \
    netcat \
    #############################################################
    ## LibreOffice packages for computer use
    #############################################################
    libreoffice-calc \
    ##############################################################
    ## Firefox packages for computer use
    ##############################################################
    # In Ubuntu 22.04, the `firefox` package is just a placeholder for a snap package, and we can't use snap in Docker (snap needs systemd)
    # We add in the Mozilla ppa so we can install an extended support release version of firefox, which does not use snap 
    firefox-esr \
    && apt-get clean

#############################################################
## Python setup, version management, and uv
#############################################################
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --set python3 /usr/bin/python3.11 \
    && ln -s /usr/bin/python3 /usr/bin/python

RUN python -m pip install --upgrade pip
RUN python -m pip install uv

##########################################################################
## Creating a directory with root only permissions
## for MCP and tools. 
## !!!!! The `model` user should not have access to this directory !!!!
##########################################################################
WORKDIR /mcp_server
RUN chmod -R 0700 /mcp_server

##########################################################################
## Copying over tools, pyproject, etc, into this
## restricted access directory
##########################################################################
COPY .. .

# Install the taiga parent package
RUN uv pip install --system -e .

RUN uv run taiga hello

WORKDIR /mcp_server/taiga-evals/libreoffice-hard1

RUN uv pip install --system -e .

##########################################################
## Configuring a workdir for the `model` user
##########################################################
ENV WORKDIR=/workdir

COPY taiga-evals/libreoffice-hard1/image/ /workdir/image

RUN chown -R model:model /workdir/image
RUN chmod -R +x /workdir/image/

RUN mkdir -p ${WORKDIR}

ENV SCREENSHOT_DIR=${WORKDIR}/screenshots

RUN mkdir -p ${SCREENSHOT_DIR}

RUN chown -R model:model ${WORKDIR}

WORKDIR ${WORKDIR}

###################################################################################################################
## Installing a VNC server for debugging
## While debugging the image, you can run the following:
## docker run -p 6080:6080 -e WIDTH=1024 -e HEIGHT=768 taiga uv --directory /mcp_server run tail -f /dev/null
## And on the host computer, visit http://localhost:6080/vnc.html and view/connect to the running docker container
## When you debug with Claude desktop, you can follow along with the model as it navigates the container
###################################################################################################################
RUN git clone --branch v1.5.0 https://github.com/novnc/noVNC.git ${WORKDIR}/noVNC && \
    git clone --branch v0.12.0 https://github.com/novnc/websockify ${WORKDIR}/noVNC/utils/websockify && \
    ln -s ${WORKDIR}/noVNC/vnc.html ${WORKDIR}/noVNC/index.html

## END: Startup scripts for Computer Use

##########################################################################
## IMPOTANT: These are default args for computer use
## These arugments configure the X11 server for the right display size
## They are used in the startup scripts at ./image/startup/
##########################################################################
ARG DISPLAY_NUM=1
ARG HEIGHT=768
ARG WIDTH=1024

ENV DISPLAY_NUM=$DISPLAY_NUM
ENV HEIGHT=$HEIGHT
ENV WIDTH=$WIDTH

##########################################################################
## This entrypoint bootstraps on startup the UI we need for computer use
## This includes:
## - Getting x11 up and running in the container
## - Setting up VNC (for debugging)
## - Setting up mutter
## - Setting up tint2 (a useful taskbar for the model)
##########################################################################
WORKDIR /mcp_server/taiga-evals/libreoffice-hard1
