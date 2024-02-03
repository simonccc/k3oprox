#!/usr/bin/env python3

# standard imports
import sys, re, os
from kopsrox_config import config, masterid, masters, workers, cname, kmsg_info, kmsg_err, kmsg_sys, kmsg_warn, s3_string, bucket, s3endpoint
from kopsrox_proxmox import get_node, qaexec, writefile
from kopsrox_k3s import get_token, k3s_rm_cluster, kubectl, k3s_update_cluster

# passed command
cmd = sys.argv[2]
kname = 'etcd-' + cmd

# check master is running / exists
# fails if node can't be found
try:
  get_node(masterid)
except:
  kmsg_err('etcd-check', 'cluster does not exist')
  exit(0)

# should check for an existing token?
# writes a etcd snapshot token from the current running clusters token
def write_token():
  # get the snapshot tokenfile
  token = get_token()

  # add a line break to the token
  token = token + '\n'

  # write the token
  with open('kopsrox.etcd.snapshot.token', 'w') as snapshot_token:
    snapshot_token.write(token)
  print(kname +'::write-token: wrote kopsrox.etcd.snapshot.token')

# run k3s s3 command passed
def s3_run(s3cmd):

  # run the command ( 2>&1 required )
  k3s_run = 'k3s etcd-snapshot ' + s3cmd + s3_string + '2>&1'
  cmd_out = qaexec(masterid, k3s_run)

  #print(cmd_out)

  # look for fatal error in output
  if re.search('level=fatal', cmd_out):
    kmsg_err('etcd-s3_run', '')
    kmsg_sys('etcd-s3_run-out', ('\n' + cmd_out))
    exit(0)

  # the response from qaexec for eg timeout
  if ( cmd_out == 'no output'):
    print('etcd::s3_run: problem with s3 ( no output ) ')
    exit(0)

  # return command outpit
  return(cmd_out)

# test connection to s3 by running ls 
s3_run('ls')

# list images in s3 storage
def list_images():

  # run s3 ls and create a list per line
  ls = s3_run('ls').split('\n')

  # images string
  images = ''

  # for each image in the sorted list
  for line in sorted(ls):

    # if image name matches the s3 line append to the images string
    if re.search(('s3://' + bucket + '/kopsrox-' + cname), line):
      images_out = line.split()
      images += images_out[0] + "\t" + images_out[2] + "\t" +  images_out[3] + '\n'

  # return images string
  return(images)

# s3 prune
if cmd == 'prune':
  kmsg_sys('etcd-prune', (s3endpoint + '/' + bucket + '\n'+s3_run('prune --name kopsrox')))
  exit(0)

# snapshot 
if cmd == 'snapshot':

  # define snapshot command
  snap_cmd = 'k3s etcd-snapshot save ' + s3_string + ' --name kopsrox --etcd-snapshot-compress'
  #print(snap_cmd)
  snapout = qaexec(masterid,snap_cmd)

  # filter output
  snapout = snapout.split('\n')
  for line in snapout:
    if re.search('upload complete', line):
      kmsg_info('etcd-snapshot-out', line)

  # check for existing token file
  if not os.path.isfile('kopsrox.etcd.snapshot.token'):
    write_token()

# print returned images
if cmd == 'list':
  kmsg_info('etcd-snapshots-list', (s3endpoint + '/' + bucket + '\n' + list_images()))
  exit

# restore
if cmd == 'restore':

  # get list of images 
  images = list_images()

  # look for passed snapshot
  try:
    if (sys.argv[3]):
      snapshot = str(sys.argv[3])
  except:
    print('etcd::restore: error pass a snapshot name eg:')
    print(images)
    exit(0)

  # check passed snapshot name exists
  if not (re.search(str(snapshot),str(images))):
    print('etcd::restore: no snapshot found:', snapshot)
    print(images)
    exit(0)

  print(kname,'restoring', snapshot)

  # removes all nodes apart from image and master
  if ( workers != 0 or masters == 3 ):
    print(kname, 'downsizing cluster for restore')
    k3s_rm_cluster(restore = True)

  write_token = writefile(masterid, 'kopsrox.etcd.snapshot.token', '/tmp/kopsrox.etcd.snapshot.token')

  # define restore command
  restore_cmd = 'systemctl stop k3s && rm -rf /var/lib/rancher/k3s/server/db/ && k3s server --cluster-reset --cluster-reset-restore-path=' + snapshot +' --token-file=/tmp/kopsrox.etcd.snapshot.token ' + s3_string

  restore = qaexec(masterid, restore_cmd)

  # display some filtered restore contents
  restout = restore.split('\n')
  for line in restout:

    # if output contains fatal error
    if re.search('level=fatal', line):
      print(line)
      print(kname, 'fatal error. exiting')
      exit(0)

    # filter these lines
    if re.search('level=', line) and not re.search('info', line) \
    and not re.search('json: no such file or directory', line) \
    and not re.search('Cluster CA certificate is trusted by the host CA bundle', line) \
    and not re.search('bootstrap key already exists', line) \
    :
      print(line)

  start = qaexec(masterid, 'systemctl start k3s')
  print(kname + ' done')

  # delete extra nodes in the restored cluster
  nodes = kubectl('get nodes').split()
  for node in nodes:

    # if matches cluster name and not master node
    if ( re.search((cname + '-'), node) and (node != ( cname + '-m1'))):
      print(kname, 'removing stale node', node)
      kubectl('delete node ' + node)

  # run k3s update
  print(kname, 'running k3s_update_cluster()')
  k3s_update_cluster()
