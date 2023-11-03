# kopsrox

- cli to automate creating a k3s cluster on proxmox VE using cloud images
- add more master/worker nodes using simple config file
- backup and restore your cluster easily via S3 snapshots
- quick demo: https://asciinema.org/a/597074

## setup prerequisites

- `sudo apt install libguestfs-tools -y`

_this is required to patch the cloudimage to install qemu-guest-agent_

- `pip3 install --break-system-packages --user -r requirements.txt`

_installs the required pip packages vs using os packages_

## Proxmox API key

Generate an API key and set the permissions:

`sudo pvesh create /access/users/root@pam/token/kopsrox`

`sudo pveum acl modify / --roles Administrator --user root@pam  --token 'root@pam!kopsrox'`

Take a note of the token as we'll need this below

## kopsrox.ini

Run `./kopsrox.py` and an example _kopsrox.ini_ will be generated

Please edit this file for your setup

Kopsrox uses a simple static id/ip assignments based on `proximgid` and `network` settings eg:

|id|proximgid|ip|type|
|--|--|--|--|
|0|170|-|image|
|1|171|192.168.0.171|master 1|
|2|172|192.168.0.172|master 2|
|3|173|192.168.0.173|master 3|
|4|174|-|spare|
|5|175|192.168.0.175|worker 1|
|6|176|192.168.0.176|worker 2|
|7|177|192.168.0.177|worker 3|
|8|178|192.168.0.178|worker 4|
|9|179|192.168.0.179|worker 5|


### [proxmox]

- __endpoint__ = `127.0.0.1` proxmox API host / IP

- __port__ = `8006` port to connect to proxmox API endpoint

- __user__ = `root@pam` - user to connect as

- __token_name__ = `kopsrox` - see api key section above

- __api_key__ = `xxxxxxxxxxxxx` - as generated above

- __proxnode__ = `proxmox` the proxmox node - the image and all nodes are created on this host

- __proxstor__ = `local-lvm` shared storage also works

- __proximgid__ = `600` - the proxmox id used for the kopsrox image/template 

- __up_image_url__ = `https://cloud-images.ubuntu.com/minimal/daily/mantic/current/mantic-minimal-cloudimg-amd64.img` - url to the cloud image you want to use as the base image

- __proxbridge__ = `vmbr0` - the bridge to use - must have internet access

### [kopsrox]

- __vm_disk__ = `20G` - size of the disk for each node in Gigs

- __vm_cpu__ = `1` - number of vcpus for each vm

- __vm_ram__ = amount of ram in G

- __cloudinituser__ = a user account for access to the vm 

- __cloudinitpass__ = password for the user

- __cloudinitsshkey__ = 

- __network__ = "network" address of proxmox cluster

- __networkgw__ = `192.168.0.1` the default gateway for the network ( must provide internet access ) 

- __netmask__ = `24` cdir netmask for the network 

### [cluster]

- __name__ = `kopsrox` name of the cluster

- __k3s_version__ = `v1.24.6+k3s1` 

- __masters__ = `1` number of master nodes - only other supported value is `3`

- __workers__ = `0` number of worker vms eg `1` - values upto `5` are supported

### [s3]

These values are optional 

- __endpoint__ = eg `s3.yourprovider.com`

- __region__ = `optional`

- __access-key__ = `393893894389`

- __access-secret__ = 

## get started
### create image

`./kopsrox.py create image`

### create a cluster

`./kopsrox.py cluster create`

### add worker

Edit `kopsrox.ini` and set `workers = 1` in the `[cluster]` section

`./kopsrox.py cluster update`

### check cluster info

`./kopsrox.py cluster info`

## commands

### image
__create__
- downloads the image file defined in `koprox.ini` as `up_image_url` under the `[proxmox]` section
- patches it ( installs packages qagent + nfs client) 
- imports the disk using `sudo qm`
- installs k3s 

__destroy__
- deletes the existing image template
- delete the .img file manually if you want a fresh download of the upstream image

__info__
- prints info about image file

## cluster
__create__
- creates and updates a cluster - use this to setup a fresh cluster
- exports kubeconfig and node token
- if a working master is found just runs `update`

__update__
- checks the state of the cluster vs what is configured in `kopsrox.ini`
- adds or deletes workers/masters per `kopsrox.ini`

__info__
- shows a list of ids, hostnames and ips the host they are running on
- shows kubectl get nodes

### kubectl
- provides a quick and basic way to run kubectl commands for example:

`./kopsrox.py cluster kubectl get events -A`

### kubeconfig
- export the kubeconfig to a `kopsrox.kubeconfig` file which is patched to have the masters IP

### destroy
- destroys the cluster ( NO WARNING! ) 

## etcd

kopsrox uses the k3s built in commands to backup to s3 api compatible storage.

tested providers include minio, cloudflare, backblaze etc

### snapshot
- create a etcd snapshot in the configured S3 storage

The first time a snapshot is taken the cluster token is written into the kopsrox directory

- `kopsrox.etcd.snapshot.token`

This is not overwriten on further snapshots are taken

`./kopsrox.py etcd snapshot`

Takes a backup of etcd

`./kopsrox.py etcd list`

Should show the new backup

### restore

Restores a cluster from an etcd snapshot

`./kopsrox.py etcd list`

Show available snapshots

`./kopsrox.py etcd restore $imagename`

- check you're using the correct `kopsrox.etcd.snapshot.token` file for the snapshot!

- downsizes the cluster to 1 node 
- some stuff not working atm

### list
- lists snapshots taken in s3 storage based on cluster name

__prune__
- deletes old snapshots by 7 days? ( tbc ) 

# FAQ
__can I use debian as a base image vs ubuntu?__

_I had to switch from debian due to some problem with a discovered interface which was dhcp and caused some network problems_

__k3s_mon 30 second timeouts?__

_Check network settings - the vms can't connect to the internet_

