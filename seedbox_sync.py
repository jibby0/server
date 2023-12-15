# rsync files from a seedbox to a local machine, exactly once, over SSH.
#
# Why?
#  sonarr requires that any Remote Path Mappings have a local path reflecting its contents. This can be done with NFS or SSHFS, but those are difficult to set up in containers, and get wonky when the remote server reboots.
#  rsync over SSH + cron doesn't care if the remote machine reboots, + easily runs in a container.

# How?
#  Usage: sonarr_sync.py my-seedbox /seedbox/path/to/data /local/working /local/metadata /local/data
#  - Get all file names in my-seedbox:/seedbox/path/to/data
#  - Get all previously processed file names in /local/metadata
#  - Diff the above to get newly added files
#  - For each new file:
#    - Copy file from my-seedbox to /local/working (used in case of transfer failure)
#    - Add file name to /local/metadata
#    - Move file to /local/data

# */1 * * * * /usr/bin/run-one /usr/bin/python3 /path/to/seedbox_sync.py <seedbox host> /seedbox/path/to/completed/ /local/path/to/downloading /local/path/to/processed /local/path/to/ready 2>&1 | /usr/bin/logger -t seedbox
# Or run it in a k8s cronjob.

import subprocess
import sys


if len(sys.argv) != 6:
    print("One or more args are undefined")
    sys.exit(1)

host, host_data_path, local_working_path, local_metadata_path, local_data_path = sys.argv[1:6]

r = subprocess.run(["ssh", host, "bash", "-c", f"IFS=$'\n'; ls {host_data_path}"], stdout=subprocess.PIPE, check=True)

available = {f for f in r.stdout.decode().split('\n') if f}

# There's better ways to list a dir locally, but using bash +ls again avoids any possible formatting discrepencies.
r = subprocess.run(["bash", "-c", f"IFS=$'\n'; ls {local_metadata_path}"], stdout=subprocess.PIPE, check=True)

processed = {f for f in r.stdout.decode().split('\n') if f}

new = available - processed

for new_file in new:
    # Be super cautious about empty file names, wouldn't want to `rm -rf` a folder by accident
    if not new_file:
        continue

    print(f"Processing: {new_file}")
    subprocess.run(["rsync", "-rsvv", f'{host}:{host_data_path}/{new_file}', f'{local_working_path}'], check=True)
    subprocess.run(["touch", f'{local_metadata_path}/{new_file}'], check=True)

    print(f"Moving to ready: {new_file}")
    try:
        subprocess.run(["mv", f'{local_working_path}/{new_file}', f'{local_data_path}'], check=True)
    except:
        subprocess.run(["rm", f'{local_metadata_path}/{new_file}'], check=True)
        raise

    subprocess.run(["rm", "-rf", f'{local_working_path}/{new_file}'], check=True)
