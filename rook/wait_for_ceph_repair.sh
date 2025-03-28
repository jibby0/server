#!/bin/bash -ex

RET=0
while [ $RET -eq "0" ]; do
	sleep 300
	date
	kubectl rook-ceph ceph status > /tmp/cephstatus
	if [ $? -eq "0" ]; then
		cat /tmp/cephstatus | grep -e 'objects misplaced' -e 'objects degraded'
		RET=$?
	fi
done

curl --fail -u ${NTFY_USER}:${NTFY_PASS} -d "no objects misplaced" ${NTFY_URL}
