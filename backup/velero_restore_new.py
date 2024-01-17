import datetime
import time
import os
import json
import subprocess
import sys

namespaces = ["vaultwarden", "postgres"]
k3s_env = {"KUBECONFIG": "/etc/rancher/k3s/k3s.yaml"}
ntfy_topic = "https://ntfy.jibby.org/velero-restore"
ntfy_auth = os.environ["NTFY_AUTH"]
restart_deployments_in = ["vaultwarden"]
restart_statefulsets_in = ["postgres"]


def main():
    if sys.version_info.major < 3 or sys.version_info.minor < 11:
        raise RuntimeError("Python 3.11 or greater required")

    velero_str = subprocess.run(
        ["/usr/local/bin/velero", "backup", "get", "-o", "json"],
        env=k3s_env,
        check=True,
        capture_output=True,
    ).stdout

    velero = json.loads(velero_str)

    backups_by_timestamp = {
        backup['metadata']['creationTimestamp']: backup
        for backup in velero['items']
    }
    if not backups_by_timestamp:
        raise ValueError("no backups?")

    newest_backup_timestamp = max(backups_by_timestamp.keys())
    one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    if datetime.datetime.fromisoformat(newest_backup_timestamp) < one_week_ago:
        raise ValueError(f"no backups < 1 week old? {newest_backup_timestamp=}")

    newest_backup = backups_by_timestamp[newest_backup_timestamp]
    print(f"Using newest backup {newest_backup['metadata']['name']}, taken at {newest_backup['metadata']['creationTimestamp']}")

    # delete namespaces
    for namespace in namespaces:
        subprocess.run(
            ["/usr/local/bin/kubectl", "delete", "namespace", namespace],
            env=k3s_env,
            check=False, # OK if this namespace doesn't exist,
        )

    # TODO check for pv with mount points in these namespaces

    subprocess.run(
        ["/usr/local/bin/velero", "restore", "create", "--from-backup", newest_backup['metadata']['name'], "--include-namespaces", ",".join(namespaces), "--wait"],
        env=k3s_env,
        check=True,
    )

    for namespace in restart_deployments_in:
        subprocess.run(
            ["/usr/local/bin/kubectl", "-n", namespace, "rollout", "restart", "deployment"],
            env=k3s_env,
            check=True,
        )
    for namespace in restart_statefulsets_in:
        subprocess.run(
            ["/usr/local/bin/kubectl", "-n", namespace, "rollout", "restart", "statefulset"],
            env=k3s_env,
            check=True,
        )
    wait_until_up("https://vaultwarden.bnuuy.org", 300)
    ntfy_send(
        f"Successfully ran velero restore for backup {newest_backup['metadata']['name']}, "
        f"{newest_backup['metadata']['creationTimestamp']}"
    )

def wait_until_up(url: str, timeout_sec: int):
    start = datetime.datetime.now()
    while True:
        try:
            subprocess.run(["curl", "--fail", url], check=True)
            return
        except subprocess.CalledProcessError as exc:
            if start + datetime.timedelta(seconds=timeout_sec) < datetime.datetime.now():
                raise ValueError(f">{timeout_sec} seconds passed & {url} is not up: {exc}")
            time.sleep(5)


def ntfy_send(data):
    # auth & payload formatting is awful in urllib. just use curl
    subprocess.run(["curl", "--fail", "-u", ntfy_auth, "-d", data, ntfy_topic], check=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        ntfy_send(f"Error running velero restore: {str(e)}")
        raise
