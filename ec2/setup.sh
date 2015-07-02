#!/bin/bash

LOG=Setup_$$.log

# Is this valid/required for AWS ?
check_project ()
{
    RESULT=$(gcutil listinstances --project=$GCE_PROJECTID 2>&1)
}

# Is this valid for AWS ?
check_keys ()
{
    echo "Check_keys - TODO"
    [[ ! -f ~/.ssh/google_compute_engine      ]] && echo "Google private key missing" && return
    [[ ! -f ~/.ssh/google_compute_engine.pub  ]] && echo "Google public key missing"  && return
}

stop_n_workers()
{
    COUNT=1
    [[ ! -z "$1" ]] && COUNT=$1
    echo "Stopping $COUNT instances :"
    INSTANCES=$(list_resources | grep worker | awk '{print $1}' | tail -n $COUNT)
    echo "$INSTANCES"
    ./aws.py stop_node $INSTANCES
}


# Start N workers in parallel ?
# This script ensures that only the specified number of workers are active
start_n_workers ()
{
    echo "In start_n_workers"
    COUNT=$1
    CURRENT=1
    out=$(list_resources | grep "swift-worker")
    if [[ "$?" == 0 ]]
    then
        echo "Current workers"
        echo "${out[*]}"
        CURRENT=$(list_resources | grep "swift-worker" | wc -l)
        echo "Count : " $CURRENT
        echo "New workers needed : $(($COUNT - $CURRENT))"
    fi

    ./aws.py start_workers $COUNT
    list_resources
}

start_n_more ()
{
    ACTIVE=$(./aws.py list_resources | grep worker | wc -l)
    MORE=$1
    start_workers $(printf "swift-worker-%03d " $(seq $(($ACTIVE+1)) 1 $(($ACTIVE+$MORE)) ) )
    list_resources
}

stop_headnode()
{
    echo "Stopping headnode"
    ./aws.py stop_headnode
}

list_resources()
{
    ./aws.py list_resources
}

dissolve()
{
    ./aws.py dissolve
}

start_headnode()
{
    ./aws.py start_headnode
}

connect()
{
    source configs
    NODE=$1
    [[ -z $1 ]] && NODE="headnode"
    [[ -z $AWS_USERNAME ]] && AWS_USERNAME="ec2-user"

    RESOURCE=($(./aws.py list_resource $NODE))
    IP=${RESOURCE[4]}

    REGION_KEYFILE=$AWS_KEYPAIR_DIR/$AWS_KEYPAIR_NAME.$AWS_REGION.pem

    echo "Connecting to AWS node:$NODE on $IP as $AWS_USERNAME"
    echo "    ssh -A -o StrictHostKeyChecking=no -l $AWS_USERNAME -i $REGION_KEYFILE $IP"
    ssh -A -o StrictHostKeyChecking=no -l $AWS_USERNAME -i $REGION_KEYFILE $IP
}


init()
{
    source configs
    start_headnode
    start_workers $AWS_WORKER_COUNT
    list_resources
}
#init
