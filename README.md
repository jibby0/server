# Ceph & Docker Swarm hyperconverged node setup

0. For a new installation, follow https://docs.ceph.com/en/latest/cephadm/install/ to bootstrap a cluster & deploy your first node.
1. Set `hosts` & run `ansible-playbook playbook.yml` to preconfigure the new node.
2. Follow "Adding Hosts" to add a new node to the ceph cluster. Add this node as a monitor and/or manager if necessary.
3. Follow https://docs.docker.com/engine/swarm/swarm-tutorial/add-nodes/ to add this node to Docker Swarm.