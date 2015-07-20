#!/bin/bash

KEY="keys/klab-wikitest-pair.us-west-2.pem"

disks(){
    IP=$1
    scp -i $KEY ./disks.sh ubuntu@$IP:~/
    ssh -A -o StrictHostKeyChecking=no -i $KEY ubuntu@$IP "sudo /home/ubuntu/disks.sh"
}

for IP in $(cat worker_ips)
#for IP in $(cat worker_ips | head -n 2)
do
    echo $IP
    ssh-keygen -f "$HOME/.ssh/known_hosts" -R $IP
    #ssh -A -o StrictHostKeyChecking=no -i $KEY ubuntu@$IP "ls -thor /mnt/swift_splitter-run003/jobs/t/*; ps -aux | grep worker.pl"
    #ssh -A -o StrictHostKeyChecking=no -i $KEY ubuntu@$IP "sudo killall worker.pl"
    #ssh -A -o StrictHostKeyChecking=no -i $KEY ubuntu@$IP "df -h"
    #ssh -A -o StrictHostKeyChecking=no -i $KEY ubuntu@$IP "sudo apt-get install -y python-lxml" &
    ssh -A -o StrictHostKeyChecking=no -i $KEY ubuntu@$IP 'python -c "import lxml; print \"Helloworld\""'
    #ssh -A -o StrictHostKeyChecking=no -i $KEY ubuntu@$IP 'ps -aux | grep python'
    echo "=============================================================="
done
