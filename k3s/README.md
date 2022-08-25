# k3s

curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --cluster-init" sh -
export NODE_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
curl -sfL https://get.k3s.io | K3S_TOKEN=$NODE_TOKEN INSTALL_K3S_EXEC="server --server https://192.168.122.87:6443" INSTALL_K3S_VERSION=v1.23.6+k3s1 sh -


# rook

KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install --create-namespace --namespace rook-ceph rook-ceph rook-release/rook-ceph:1.9.2 -f rook-ceph-values.yaml

KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm install --create-namespace --namespace rook-ceph rook-ceph-cluster --set operatorNamespace=rook-ceph rook-release/rook-ceph-cluster:1.9.2 -f rook-ceph-cluster-values.yaml

## things in the rook folder

## reference
https://github.com/rook/rook/blob/677d3fa47f21b07245e2e4ab6cc964eb44223c48/Documentation/Storage-Configuration/Shared-Filesystem-CephFS/filesystem-storage.md

If important data is on CephBlockPool-backed PVCs, don't forget to set the PV's persistentVolumeReclaimPolicy to `Retain`.

## tolerations
If your setup divides k8s nodes into ceph & non-ceph nodes (using a label, like `storage-node=true`), ensure labels & a toleration are set properly (`storage-node=false`, with a toleration checking for `storage-node`) so non-ceph nodes still run PV plugin Daemonsets.

# nvidia driver (on debian)
curl -s -L https://nvidia.github.io/nvidia-container-runtime/gpgkey |   sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-container-runtime/$distribution/nvidia-container-runtime.list |   sudo tee /etc/apt/sources.list.d/nvidia-container-runtime.list

wget https://developer.download.nvidia.com/compute/cuda/11.6.2/local_installers/cuda-repo-debian11-11-6-local_11.6.2-510.47.03-1_amd64.deb
sudo dpkg -i cuda-repo-debian11-11-6-local_11.6.2-510.47.03-1_amd64.deb
sudo apt-key add /var/cuda-repo-debian11-11-6-local/7fa2af80.pub
sudo apt-get update

## install kernel headers

sudo apt install cuda nvidia-container-runtime nvidia-kernel-dkms

sudo apt install --reinstall nvidia-kernel-dkms
## verify dkms is actually running

sudo vi /etc/modprobe.d/blacklist-nvidia-nouveau.conf

blacklist nouveau
options nouveau modeset=0

sudo update-initramfs -u

## configure containerd to use nvidia by default

Copy https://github.com/k3s-io/k3s/blob/v1.24.2%2Bk3s2/pkg/agent/templates/templates_linux.go into /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl (substitute your k3s version)

Edit the file:

<... snip>
  conf_dir = "{{ .NodeConfig.AgentConfig.CNIConfDir }}"
{{end}}
[plugins.cri.containerd.runtimes.runc]
  runtime_type = "io.containerd.runc.v2"

[plugins.cri.containerd.runtimes.runc.options]
  BinaryName = "/usr/bin/nvidia-container-runtime"

{{ if .PrivateRegistryConfig }}
<... snip>


& then `systemctl restart k3s`

Label your GPU-capable nodes: `kubectl label nodes <node name> gpu-node=true`

& then install the nvidia device plugin:

helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade -i nvdp nvdp/nvidia-device-plugin --version=0.12.2 --namespace nvidia-device-plugin --create-namespace --set-string nodeSelector.gpu-node=true


Ensure the pods on the namespace are Running.

Test GPU passthrough by applying examples/cuda-pod.yaml, then exec-ing into it & running `nvidia-smi`.

Currently, 1 GPU = 1 pod can use the GPU.

# ceph client

sudo apt install ceph-fuse

sudo vi /etc/fstab

192.168.1.1.,192.168.1.2:/    /ceph   ceph    name=admin,secret=<secret key>,x-systemd.mount-timeout=5min,_netdev,mds_namespace=data


# disable mitigations
https://unix.stackexchange.com/questions/554908/disable-spectre-and-meltdown-mitigations

# Monitoring

https://rpi4cluster.com/monitoring/k3s-grafana/

Tried https://github.com/prometheus-operator/kube-prometheus. The only way to persist dashboards is to add them to Jsonnet & apply the generated configmap.

# libvirtd

...

# Still to do

deluge?
gogs ingress (can't go through cloudflare without cloudflared on the client)
