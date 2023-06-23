#!/usr/bin/env python3

import os, re, sys
import kopsrox_ini as ini

# generate barebones kopsrox.ini if it doesn't exist
conf = ini.conf
if not os.path.isfile(conf):
  ini.init_kopsrox_ini()

import kopsrox_proxmox as proxmox
import common_config as common

from configparser import ConfigParser
config = ConfigParser()

# read ini files
config.read(conf)

# proxmox checks
endpoint = common.conf_check(config,'proxmox','endpoint',conf)
user = common.conf_check(config,'proxmox','user',conf)
token_name = common.conf_check(config,'proxmox','token_name',conf)
api_key = common.conf_check(config,'proxmox','api_key',conf)

# proxmox -> kopsrox config checks
proxnode = common.conf_check(config,'proxmox','proxnode',conf)
proxstor = common.conf_check(config,'proxmox','proxstor',conf)
proximgid = common.conf_check(config,'proxmox','proximgid',conf)
up_image_url = common.conf_check(config,'proxmox','up_image_url',conf)
proxbridge = common.conf_check(config,'proxmox','proxbridge',conf)

# kopsrox config checks
vm_disk = common.conf_check(config,'kopsrox','vm_disk',conf)
vm_cpu = common.conf_check(config,'kopsrox','vm_cpu',conf)
vm_ram = common.conf_check(config,'kopsrox','vm_ram',conf)

# cloudinit
cloudinituser = common.conf_check(config,'kopsrox','cloudinituser',conf)
cloudinitpass = common.conf_check(config,'kopsrox','cloudinitpass',conf)
cloudinitsshkey = common.conf_check(config,'kopsrox','cloudinitsshkey',conf)

# network
network = common.conf_check(config,'kopsrox','network',conf)
networkgw = common.conf_check(config,'kopsrox','networkgw',conf)
netmask = common.conf_check(config,'kopsrox','netmask',conf)

# cluster level checks
masters = common.conf_check(config,'cluster','masters',conf)
workers = common.conf_check(config,'cluster','workers',conf)
k3s_version = common.conf_check(config,'cluster','k3s_version',conf)

# master check - can only be 1 or 3
if not ( (int(masters) == 1) or(int(masters) == 3)):
  print ('ERROR: only 1 or 3 masters supported. You have:', masters)
  exit(0)

# check connection to proxmox
prox = proxmox.prox_init()
# if unable to get cluster status
if not prox.cluster.status.get():
  print('ERROR: unable to connect to proxmox - check proxmox.ini')
  exit(0)

# get list of nodes
nodes = prox.nodes.get()
if not (re.search(proxnode, (str(nodes)))):
  print(proxnode, 'node not found - working nodes are:')
  for i in nodes:
    print(i.get("node"))
  exit(0)

# check configured storage on cluster
storage = prox.nodes(proxnode).storage.get()
if not (re.search(proxstor, (str(storage)))):
  print(proxstor, 'storage not found - available storage:')
  for i in storage:
    print(i.get("storage"))
  exit(0)

# check configured bridge on cluster
bridge = prox.nodes(proxnode).network.get()
if not (re.search(proxbridge, (str(bridge)))):
  print(proxbridge, 'bridge not found - available:')
  for i in bridge:
    if i.get("type") == 'bridge':
      print(i.get("iface"))
  exit(0)

# skip image check if image create is passed
try:
  # check for image create command line
  if not ((str(sys.argv[1]) == str('image')) and (str(sys.argv[2]) == str('create'))):
    exit(1)
except:
  kopsrox_img = common.kopsrox_img(proxstor,proximgid)
  images = prox.nodes(proxnode).storage(proxstor).content.get()

  # search the returned list of images
  if not (re.search(kopsrox_img, str(images))):
    print(kopsrox_img, 'not found on '+ proxnode + ':' + proxstor)
    print('run kopsrox image create')
    exit(0)

# check any existing vm's are powered on
for vmid in (proxmox.list_kopsrox_vm()):

  # vm not powered on check
  vmi = proxmox.vm_info(vmid)

  # power on all nodes aside from image
  if (( vmi.get('status') == 'stopped') and ( int(vmid) != int(proximgid) )):
    print('WARN: powering on', vmi.get('name'))
    poweron = prox.nodes(proxnode).qemu(vmid).status.start.post()
    proxmox.task_status(prox, str(poweron), proxnode)
