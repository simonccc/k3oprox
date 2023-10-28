#!/usr/bin/env python3

# used by eg kubectl
import kopsrox_proxmox as proxmox

from configparser import ConfigParser

# verbs
top_verbs = ['image', 'cluster', 'etcd']
verbs_image = ['info', 'create', 'destroy']
verbs_cluster = ['info', 'create', 'update', 'destroy', 'kubectl', 'kubeconfig']
verbs_etcd = ['snapshot', 'restore', 'list', 'prune']

# config dict
kopsrox_config = ConfigParser()
kopsrox_config.read('kopsrox.ini')
config = ({s:dict(kopsrox_config.items(s)) for s in kopsrox_config.sections()})

# used items
proximgid = int(config['proxmox']['proximgid'])
proxnode = config['proxmox']['proxnode']

# get token and strip linebreak
def get_token():
  f = open("kopsrox.k3stoken", "r")
  return(f.read().rstrip())

# kubectl
def kubectl(masterid,cmd):
  k = str(('/usr/local/bin/k3s kubectl ' +cmd))
  kcmd = proxmox.qaexec(masterid,k)
  return(kcmd)

# return a list of valid koprox vms
def vmnames():
  vmid = proximgid
  vmnames = []
  for vmid in proxmox.list_kopsrox_vm():
    if ( vmid > proximgid ):
      vmnames.append(vmname(vmid))
  return(vmnames)

# look up vmid from name
def vmname2id(name):
  vmid = proximgid
  while ( vmid <= (int(proximgid) + 9 )):
    # if match return id
    if ( name == vmname(int(vmid)) ):
      return(int(vmid))
    vmid = (int(vmid) + 1)

# map id to hostname
def vmname(vmid):
    cname = config['cluster']['name']
    vmid = int(vmid)
    names = { 
            (proximgid): cname +'-image',
            (proximgid + 1 ): cname + '-m1',
            (proximgid + 2 ): cname + '-m2', 
            (proximgid + 3 ): cname + '-m3', 
            (proximgid + 4 ): cname + '-u1', 
            (proximgid + 5 ): cname + '-w1', 
            (proximgid + 6 ): cname + '-w2', 
            (proximgid + 7 ): cname + '-w3', 
            (proximgid + 8 ): cname + '-w4', 
            (proximgid + 9 ): cname + '-w5', 
            }
    return(names[vmid])

# kubeconfig
def kubeconfig(masterid):
    ip = vmip(masterid)
    kubeconfig = proxmox.qaexec(masterid, 'cat /etc/rancher/k3s/k3s.yaml')

    # replace localhost with masters ip
    kubeconfig = kubeconfig.replace('127.0.0.1', ip)

    # write file out
    with open('kopsrox.kubeconfig', 'w') as kubeconfig_file:
      kubeconfig_file.write(kubeconfig)

# node token
def k3stoken(masterid):
    token = proxmox.qaexec(masterid, 'cat /var/lib/rancher/k3s/server/node-token')
    with open('kopsrox.k3stoken', 'w') as k3s:

      # this function name seems weird
      k3s.write(token)

# pass a vmid return the IP
def vmip(vmid):
  network = config['kopsrox']['network']
  network_octs = network.split('.')
  basenetwork = ( network_octs[0] + '.' + network_octs[1] + '.' + network_octs[2] + '.' )

  # generate the last ip
  ip = basenetwork + str(int(network_octs[-1]) + ( int(vmid) - int(proximgid)))
  return(ip)
