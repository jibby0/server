FROM python:3.11-alpine
RUN apk update && \
    apk add openssh bash rsync && \
    apk cache clean
# We need a real user to use SSH. https://superuser.com/questions/1761504/openssh-allow-nonexistent-user-to-login
RUN addgroup -g 1000 nonroot && \
    adduser -u 1000 nonroot -G nonroot -s /bin/bash -S
