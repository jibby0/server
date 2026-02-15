# https://hub.docker.com/repository/docker/jibby0/server-magicmirror
#
# Add gkeepapi to support https://github.com/taxilof/MMM-GoogleKeep
FROM karsten13/magicmirror:v2.34.0_fat

USER root

RUN apt-get update && \
    apt-get install -y python3-pip vim-tiny && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/apt/lists/*

USER node:node

RUN pip3 install -U gkeepapi --break-system-packages
