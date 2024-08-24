# k3s + rook Homelab

_Writeup still a WIP, please pardon the dust._

_Below is mostly braindumps & rough commands for creating/tweaking these services. Formal writeup coming soon!_

# k3s

## installing k3s

```
# First node
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.29.6+k3s2 INSTALL_K3S_EXEC="server --cluster-init" sh -
export NODE_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)

# Remaining nodes
curl -sfL https://get.k3s.io | K3S_TOKEN=$NODE_TOKEN INSTALL_K3S_VERSION=v1.29.6+k3s2 INSTALL_K3S_EXEC="server --server https://<server node ip>:6443 --kubelet-arg=allowed-unsafe-sysctls=net.ipv4.*,net.ipv6.conf.all.forwarding" sh -
```


## upgrading k3s

https://docs.k3s.io/upgrades/automated

## purging k3s image cache

```
$ sudo crictl rmi --prune
```

## limiting log size

(Shouldn't be a problem on newer Debian, where rsyslog is not in use.)

In /etc/systemd/journald.conf, set "SystemMaxUse=100M"

In /etc/logrotate.conf, set "size 100M"

## purging containerd snapshots

https://github.com/containerd/containerd/blob/main/docs/content-flow.md

containerd really doesn't want you batch-deleting snapshots.

https://github.com/k3s-io/k3s/issues/1905#issuecomment-820554037

```
for sha in $(sudo k3s ctr snapshot usage | awk '{print $1}'); do sudo k3s ctr snapshot rm $sha && echo $sha; done
```

Run this a few times until it stops returning results.

## ingress

Uses traefik, the k3s default.

externalTrafficPolicy: Local is used to preserve forwarded IPs.

A `cluster-ingress=true` label is given to the node my router is pointing to. Some services use a nodeAffinity to request it.

For traefik, this is a harmless optimization to reduce traffic hairpinning. For pods with `hostNetwork: true`, this ensures they run on the node with the right IP.

# rook

## installing rook

See `rook/rook-ceph-operator-values.yaml` and `rook/rook-ceph-cluster-values.yaml`.

## upgrading rook

https://rook.io/docs/rook/latest-release/Upgrade/rook-upgrade/?h=upgrade

## upgrading ceph

https://rook.io/docs/rook/latest-release/Upgrade/ceph-upgrade/?h=upgrade

## Finding the physical device for an OSD

`ceph osd metadata <id> | grep -e '"hostname"' -e '"bluestore_bdev_dev_node"'`

```
$ ceph osd metadata osd.1 | grep -e '"hostname"' -e '"bluestore_bdev_dev_node"'
    "bluestore_bdev_dev_node": "/dev/sdd",
    "hostname": "node1",
```

## tolerations

My setup divides k8s nodes into ceph & non-ceph nodes (using the label `storage-node=true`).

Ensure labels & a toleration are set properly, so non-rook nodes can still run PV plugin Daemonsets. I accomplished this with a `storage-node=false` label on non-rook nodes, with a toleration checking for `storage-node`.

Otherwise, any pod scheduled on a non-ceph node won't be able to mount ceph-backed PVCs.

See `rook-ceph-cluster-values.yaml->cephClusterSpec->placement` for an example.

## CephFS

### EC backing pool

EC-backed filesystems require a regular replicated pool as a default.

https://lists.ceph.io/hyperkitty/list/ceph-users@ceph.io/thread/QI42CLL3GJ6G7PZEMAD3CXBHA5BNWSYS/
https://tracker.ceph.com/issues/42450

Then setfattr a directory on the filesystem with an EC-backed pool. Any new data written to the folder will go to the EC-backed pool.

setfattr -n ceph.dir.layout.pool -v cephfs-erasurecoded /mnt/cephfs/my-erasure-coded-dir

https://docs.ceph.com/en/quincy/cephfs/file-layouts/

### Sharing 1 CephFS instance between multiple PVCs

https://github.com/rook/rook/blob/677d3fa47f21b07245e2e4ab6cc964eb44223c48/Documentation/Storage-Configuration/Shared-Filesystem-CephFS/filesystem-storage.md

Create CephFilesystem
Create SC backed by Filesystem & Pool
Ensure the CSI subvolumegroup was created. If not, `ceph fs subvolumegroup create <fsname> csi`
Create PVC without a specified PV: PV will be auto-created
_Super important_: Set created PV to ReclaimPolicy: Retain
Create a new, better-named PVC

### Resizing a CephFS PVC
Grow resources->storage on PV
Grow resources->storage on PVC

Verify the new limit: `getfattr -n ceph.quota.max_bytes /mnt/volumes/csi/csi-vol-<uuid>/<uuid>`

## Crush rules for each pool

 for i in `ceph osd pool ls`; do echo $i: `ceph osd pool get $i crush_rule`; done

On ES backed pools, device class information is in the erasure code profile, not the crush rule.
https://docs.ceph.com/en/latest/dev/erasure-coded-pool/

 for i in `ceph osd erasure-code-profile ls`; do echo $i: `ceph osd erasure-code-profile get $i`; done


## ObjectStore

If hostNetwork is enabled on the cluster, ensure rook-ceph-operator is not running with hostNetwork enable. It doesn't need host network access to orchestrate the cluster, & impedes orchestration of objectstores & associated resources.

## public s3-interface bucket listing w/ HTML

This is great for setting up easy public downloads.

- Create a user (see `rook/buckets/user-josh.yaml`)
- `kubectl -n rook-ceph get secret rook-ceph-object-user-ceph-objectstore-josh -o go-template='{{range $k,$v := .data}}{{printf "%s: " $k}}{{if not $v}}{{$v}}{{else}}{{$v | base64decode}}{{end}}{{"\n"}}{{end}}`
- Create bucket (`rook/buckets/bucket.py::create_bucket`)
- Set policy (`rook/buckets/bucket.py::set_public_read_policy`)
- Upload file
```python
from bucket import *
conn = connect()
conn.upload_file('path/to/s3-bucket-listing/index.html', 'public', 'index.html', ExtraArgs={'ContentType': 'text/html'})
```


# nvidia driver (on debian)

```
curl -s -L https://nvidia.github.io/nvidia-container-runtime/gpgkey |   sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-container-runtime/$distribution/nvidia-container-runtime.list |   sudo tee /etc/apt/sources.list.d/nvidia-container-runtime.list

wget https://developer.download.nvidia.com/compute/cuda/11.6.2/local_installers/cuda-repo-debian11-11-6-local_11.6.2-510.47.03-1_amd64.deb
sudo dpkg -i cuda-repo-debian11-11-6-local_11.6.2-510.47.03-1_amd64.deb
sudo apt-key add /var/cuda-repo-debian11-11-6-local/7fa2af80.pub
sudo apt-get update
```

## install kernel headers

```
sudo apt install cuda nvidia-container-runtime nvidia-kernel-dkms

sudo apt install --reinstall nvidia-kernel-dkms
```

## verify dkms is actually running

```
sudo vi /etc/modprobe.d/blacklist-nvidia-nouveau.conf

blacklist nouveau
options nouveau modeset=0

sudo update-initramfs -u
```

## configure containerd to use nvidia by default

Copy https://github.com/k3s-io/k3s/blob/v1.24.2%2Bk3s2/pkg/agent/templates/templates_linux.go into `/var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl` (substitute your k3s version)

Edit the file to add a `[plugins.cri.containerd.runtimes.runc.options]` section:

```
<... snip>
  conf_dir = "{{ .NodeConfig.AgentConfig.CNIConfDir }}"
{{end}}
[plugins.cri.containerd.runtimes.runc]
  runtime_type = "io.containerd.runc.v2"

[plugins.cri.containerd.runtimes.runc.options]
  BinaryName = "/usr/bin/nvidia-container-runtime"

{{ if .PrivateRegistryConfig }}
<... snip>
```


& then `systemctl restart k3s`

Label your GPU-capable nodes: `kubectl label nodes <node name> gpu-node=true`

& then install the nvidia device plugin:

```
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade -i nvdp nvdp/nvidia-device-plugin --version=0.12.2 --namespace nvidia-device-plugin --create-namespace --set-string nodeSelector.gpu-node=true
```


Ensure the pods on the namespace are Running.

Test GPU passthrough by applying `examples/cuda-pod.yaml`, then exec-ing into it & running `nvidia-smi`.

## Share NVIDIA GPU

https://github.com/NVIDIA/k8s-device-plugin#shared-access-to-gpus-with-cuda-time-slicing

```yaml
version: v1
sharing:
  timeSlicing:
    renameByDefault: false
    failRequestsGreaterThanOne: false
    resources:
    - name: nvidia.com/gpu
      replicas: 5
```

```
$ helm upgrade -i nvdp nvdp/nvidia-device-plugin ... --set-file config.map.config=nvidia-device-plugin-config.yaml
```

# ceph client for cephfs volumes

## New method

https://docs.ceph.com/en/latest/man/8/mount.ceph/

```
sudo mount -t ceph user@<cluster FSID>.<filesystem name>=/ /mnt/ceph -o secret=<secret key>,x-systemd.requires=ceph.target,x-systemd.mount-timeout=5min,_netdev,mon_addr=192.168.1.1
```

## Older method (stopped working for me around Pacific)

```
sudo vi /etc/fstab

192.168.1.1,192.168.1.2:/    /ceph   ceph    name=admin,secret=<secret key>,x-systemd.mount-timeout=5min,_netdev,mds_namespace=data
```

# disable mitigations
https://unix.stackexchange.com/questions/554908/disable-spectre-and-meltdown-mitigations

# Monitoring

https://rpi4cluster.com/monitoring/monitor-intro/, + what's in the `monitoring` folder.

Tried https://github.com/prometheus-operator/kube-prometheus. The only way to persist dashboards is to add them to Jsonnet & apply the generated configmap. I'm not ready for that kind of IaC commitment in a homelab.

# Exposing internal services

## kubectl expose

```
kubectl expose svc/some-service --name=some-service-external --port 1234 --target-port 1234 --type LoadBalancer
```

Service will then be available on port 1234 of any k8s node.

## using a lan-only domain

An A record for `lan.jibby.org` & `*.lan.jibby.org` points to an internal IP.

To be safe, a middleware is included to filter out source IPs outside of the LAN network & k3s CIDR. See `traefik/middleware-lanonly.yaml`.

Then, internal services can be exposed with an IngressRoute, as a subdomain of `lan.jibby.org`. See `sonarr.yaml`'s IngressRoute.

# Backups

My backups target is a machine running
- k3s
- minio
- velero

Important services are backed up with velero to the remote minio instance. These backups are restored to the remote k3s instance to ensure functionality.

## installing velero
```
KUBECONFIG=/etc/rancher/k3s/k3s.yaml velero install \
 --provider aws \
 --plugins velero/velero-plugin-for-aws:v1.0.0 \
 --bucket velero  \
 --secret-file ./credentials-velero  \
 --use-volume-snapshots=true \
 --default-volumes-to-fs-backup \
 --use-node-agent \
 --backup-location-config region=default,s3ForcePathStyle="true",s3Url=http://172.16.69.234:9000  \
 --snapshot-location-config region="default"
```

Had to remove `resources:` from the daemonset.

### Change s3 target after install
```
kubectl -n velero edit backupstoragelocation default
```

### Using a local storage storageClass in the target

https://velero.io/docs/v1.3.0/restore-reference/

Velero does not support hostPath PVCs, but works just fine with the `openebs-hostpath` storageClass.

```
KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm install openebs --namespace openebs openebs/openebs --create-namespace --set localprovisioner.basePath=/k3s-storage/openebs
```

This is a nice PVC option for simpler backup target setups.


# [WIP] Still to do

- real failover
  - https://metallb.universe.tf/concepts/layer2/
- bittorrent + VPN
- gogs ssh ingress?
  - can't go through cloudflare without cloudflared on the client
  - cloudflared running in the gogs pod?
  - do gitea or gitlab have better options?
- Bonded interface for n5105s
- more reproducable node setup
  - newer kernel too
- more reproducable kubernetes setup (? too much work)
  - https://elemental.docs.rancher.com/quickstart-cli/
- authelia for internal services
  - maybe once the helm chart is a little smoother
  - can it allow tidbyt access?

# [WIP] What's important on each node?

- /var/lib/rook
- /var/lib/rancher
- /run/k3s
- /var/lib/kubelet/pods
- /etc/rancher/k3s/

- /etc/sysctl.d/98-openfiles.conf
   fs.inotify.max_user_instances = 1024
   fs.inotify.max_user_watches = 1048576
- non-free: https://wiki.debian.org/SourcesList#Example_sources.list
  apt install firmware-misc-nonfree
