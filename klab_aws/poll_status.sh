#!/bin/bash


disks(){
    IP=$1
    scp -i keys/klab-wikitest-pair.us-west-2.pem ./disks.sh ubuntu@$IP:~/
    ssh -A -o StrictHostKeyChecking=no -i keys/klab-wikitest-pair.us-west-2.pem ubuntu@$IP "sudo /home/ubuntu/disks.sh"
}
for IP in $(cat worker_ips)
#for IP in $(cat worker_ips | head -n 2)
do
    echo $IP
    #ssh -A -o StrictHostKeyChecking=no -i keys/klab-wikitest-pair.us-west-2.pem ubuntu@$IP "ls -thor /mnt/swift_splitter-run003/jobs/t/*; ps -aux | grep worker.pl"
    #ssh -A -o StrictHostKeyChecking=no -i keys/klab-wikitest-pair.us-west-2.pem ubuntu@$IP "sudo killall worker.pl"
    #disks $IP &
    ssh -A -o StrictHostKeyChecking=no -i keys/klab-wikitest-pair.us-west-2.pem ubuntu@$IP "df -h"
    #ssh -A -o StrictHostKeyChecking=no -i keys/klab-wikitest-pair.us-west-2.pem ubuntu@$IP 'ps -aux | grep python'
    echo "=============================================================="
done
