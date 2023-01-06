#!/bin/bash -e

# Usage: sonarr_sync.sh my-seedbox /seedbox/path/to/data /local/working /local/metadata /local/data
# Get all file names in HOST:HOST_DATA_PATH
# Get all previously processed file names in LOCAL_METADATA_PATH
# Diff the above to get newly added files
# For each new file:
#   Copy file to LOCAL_WORKING_PATH (used in case of transfer failure)
#   Add file name to LOCAL_METADATA_PATH
#   Move file to LOCAL_DATA_PATH


HOST=$1
HOST_DATA_PATH=$2
LOCAL_WORKING_PATH=$3
LOCAL_METADATA_PATH=$4
LOCAL_DATA_PATH=$5

if [[ -z $HOST || -z $HOST_DATA_PATH || -z $LOCAL_WORKING_PATH || -z $LOCAL_METADATA_PATH || -z $LOCAL_DATA_PATH ]]; then
  echo 'one or more args are undefined'
  exit 1
fi

ssh $HOST bash -c 'OIFS=$IFS; IFS=$'"'\n'"'; available=($(ls '$HOST_DATA_PATH')); IFS=$OIFS; declare -p available' > /tmp/available
source /tmp/available
rm /tmp/available

#declare -p available


bash -c 'OIFS=$IFS; IFS=$'"'\n'"'; processed=($(ls '$LOCAL_METADATA_PATH')); IFS=$OIFS; declare -p processed' > /tmp/processed
source /tmp/processed
rm /tmp/processed

#declare -p processed

OIFS=$IFS
IFS=$'\n'
new=($(comm --nocheck-order -13 <(printf '%s\n' "${processed[@]}" | LC_ALL=C sort) <(printf '%s\n' "${available[@]}" | LC_ALL=C sort)))
IFS=$OIFS

#declare -p new

for i in "${new[@]}"
do
	if [ ! -z "$i" ]; then
		echo "Processing: $i"
		rsync -rsvv "$HOST:$HOST_DATA_PATH/$i" $LOCAL_WORKING_PATH
		touch "$LOCAL_METADATA_PATH/$i"
		echo "Moving to ready: $i"
		rsync -r "$LOCAL_WORKING_PATH/$i" "$LOCAL_DATA_PATH"
		rm -rf "$LOCAL_WORKING_PATH/$i"
	fi
done
