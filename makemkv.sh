# one-off for making mkvs out of blu-ray dumps
docker run -d \
    --name=makemkv \
    -p 5800:5800 \
    -v /my-makemkv-config:/config:rw \
    -v /my-video/storage:/storage:ro \
    -v /my-video/output:/output:rw \
    jlesage/makemkv
