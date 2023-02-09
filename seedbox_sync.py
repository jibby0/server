import subprocess
import sys

# Usage: sonarr_sync.py my-seedbox /seedbox/path/to/data /local/working /local/metadata /local/data
# Get all file names in HOST:HOST_DATA_PATH
# Get all previously processed file names in LOCAL_METADATA_PATH
# Diff the above to get newly added files
# For each new file:
#   Copy file to LOCAL_WORKING_PATH (used in case of transfer failure)
#   Add file name to LOCAL_METADATA_PATH
#   Move file to LOCAL_DATA_PATH

if len(sys.argv) != 6:
    print("One or more args are undefined")
    sys.exit(1)

host, host_data_path, local_working_path, local_metadata_path, local_data_path = sys.argv[1:6]

r = subprocess.run(["ssh", host, "bash", "-c", f"IFS=$'\n'; ls {host_data_path}"], stdout=subprocess.PIPE, check=True)

available = {f for f in r.stdout.decode().split('\n') if f}

r = subprocess.run(["bash", "-c", f"IFS=$'\n'; ls {local_metadata_path}"], stdout=subprocess.PIPE, check=True)

processed = {f for f in r.stdout.decode().split('\n') if f}

new = available - processed

for new_file in new:
    # Be super cautious about empty file names, wouldn't want to `rm -rf` a folder by accident
    if not new_file:
        continue

    print(f"Processing: {new_file}")
    subprocess.run(["bash", "-c", f"rsync -rsvv '{host}:{host_data_path}/{new_file}' '{local_working_path}'"], check=True)
    r = subprocess.run(["bash", "-c", f"touch '{local_metadata_path}/{new_file}'"], check=True)

    print(f"Moving to ready: {new_file}")
    subprocess.run(["bash", "-c", f"rsync -r '{local_working_path}/{new_file}' '{local_data_path}'"], check=True)
    subprocess.run(["bash", "-c", f"rm -rf '{local_working_path}/{new_file}'"], check=True)
