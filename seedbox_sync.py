# rsync files from a seedbox to a local machine, exactly once, over SSH.
#
# Why?
#  *arr requires that any Remote Path Mappings have a local path reflecting its contents. This can be done with NFS or SSHFS, but those are difficult to set up in containers, and get wonky when the remote server reboots.
#  rsync over SSH + cron doesn't care if the remote machine reboots, and easily runs in a container.

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
# Or run it in a k8s cronjob. See seedbox-sync.yaml
# kubectl -n plex create configmap seedbox-sync --from-file=seedbox_sync.py


import subprocess
import sys
import concurrent.futures

if len(sys.argv) != 6:
    print("One or more args are undefined")
    sys.exit(1)

host, host_data_path, local_working_path, local_metadata_path, local_data_path = sys.argv[1:6]

r = subprocess.run(["ssh", host, "bash", "-c", f"IFS=$'\n'; ls {host_data_path}"], stdout=subprocess.PIPE, check=True)

available_files = {f for f in r.stdout.decode().split('\n') if f}

# There's better ways to list a dir locally, but using bash & ls again reduces possible formatting discrepencies.
r = subprocess.run(["bash", "-c", f"IFS=$'\n'; ls {local_metadata_path}"], stdout=subprocess.PIPE, check=True)

processed_files = {f for f in r.stdout.decode().split('\n') if f}

new_files = available_files - processed_files

def process_file(new_file: str) -> None:
    # Be super cautious about empty file names, wouldn't want to `rm -rf` a folder by accident
    if not new_file:
        return

    print(f"Processing: {new_file}")
    subprocess.run(["rsync", "-rsvv", f'{host}:{host_data_path}/{new_file}', f'{local_working_path}'], check=True)
    subprocess.run(["touch", f'{local_metadata_path}/{new_file}'], check=True)

    print(f"Moving to ready: {new_file}")
    try:
        subprocess.run(["mv", f'{local_working_path}/{new_file}', f'{local_data_path}'], check=True)
    except:
        subprocess.run(["rm", f'{local_metadata_path}/{new_file}'], check=False)
        raise

    subprocess.run(["rm", "-rf", f'{local_working_path}/{new_file}'], check=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    future_to_new_files = {executor.submit(process_file, new_file): new_file for new_file in new_files}
    for future in concurrent.futures.as_completed(future_to_new_files):
        new_file = future_to_new_files[future]
        try:
            data = future.result()
            print(f"Processed {new_file}")
        except Exception as exc:
            print(f"{new_file} generated an exception: {exc}")
