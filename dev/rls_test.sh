set -e
#set -x

start_time=$(date +%s) 

# vars
CFG="kopsrox.ini"
K="./kopsrox.py"
KC="$K cluster"
KCI="$KC info"
KCC="$KC create"
KCU="$KC update"
KCD="$KC destroy"
KI="$K image"
KID="$KI destroy"
KIC="$KI create"
KII="$KI info"
KE="$K etcd"
KEL="$K list"
KES="$KE snapshot"
KER="$KE restore"
KERL="${KER}-latest"


# change 
kc() {
  sed -i /"$1 =/c\\$1 = $2" $CFG
}

# get pods
get_pods="$KC kubectl get pods -A"

# 0 size cluster
kc workers 0 ; kc masters 1
$KCD

# create image
$KIC

# create / update cluster
$KCC ; $KCU

# take snapshot
$KES

# destroy cluster
$KCD

# create / update cluster
$KCC ; $KCU

# restore snapshot
$KERL

# update cluster
$KCU

# add a worker and delete it
kc workers 1 ; $KCU ; kc workers 0 ; $KCU

# re add worker
kc workers 1 ; $KCU 

# add 3 masters and go back to 1
kc masters 3 ; $KCU ; kc masters 1  ; $KCU

# add 3 masters 
kc masters 3 ; $KCU 

# take snapshot
$KES

# destroy cluster
$KCD

# create / update cluster
$KCC ; $KCU
#
# # restore snapshot
$KERL
#
# update cluster
$KCU

# change back to 1 node
kc masters 1 ; $KCU ; kc workers 0  ; $KCU

# destroy cluster
$KCD

# create / update cluster
$KCC ; $KCU
#restore snapshot
$KERL


finish_time=$(date +%s) 
echo  $((finish_time - start_time)) secs