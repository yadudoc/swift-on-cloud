#!/bin/bash


source setup.sh

list_resources | grep "sworker" | awk '{print $7}' > worker_list

RESOURCE=($(./aws.py list_resource "swift-headnode"))
IP=${RESOURCE[4]}

REGION_KEYFILE=$AWS_KEYPAIR_DIR/$AWS_KEYPAIR_NAME.$AWS_REGION.pem
ls $REGION_KEYFILE
exit 0


