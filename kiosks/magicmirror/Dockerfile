FROM karsten13/magicmirror:v2.34.0_fat

USER root

RUN npm install -g python-shell pm2
#RUN apt-get update && \
#    apt-get install -y python-shell && \
#    apt-get clean autoclean && \
#    apt-get autoremove --yes && \
#    rm -rf /var/lib/apt/lists/*


USER node:node
