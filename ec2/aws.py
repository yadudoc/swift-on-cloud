#!/usr/bin/env python
# References :  https://github.com/tomcz/aws_vpc_py/blob/master/aws.py
# This reference uses an MIT like licence with the only requirement being that the
# original copyright notice is included.

import datetime
import time
import configurator
import cloud_libs as cloud
import os
import logging
import sys

#==================================================================================
# Global defs
#==================================================================================
HEADNODE_NAME="swift-headnode"
ERR_CODE={'HEADNODE_NO_IP': 5,
          'HEADNODE_NO_EXIST': 6,
          'CONFIG_SANITY_FAIL': 2}
#==================================================================================

def help():
    help_string = """ Usage for aws.py : python aws.py [<option> <arguments...>]
    list_resources           : List all resources
    list_resource <id/name>  : List the public ip and state of the resource
    start_headnode           : Starts the headnode, to which workers connect to
    stop_headnode            : Terminates the headnode
    start_workers <count>    : Starts count workers returns a list of unique ids
    stop_nodes    <count>    : Starts count workers returns a list of unique ids
    stop_node     <id>*      : Terminates the node which matches the id with its name or unique id
    dissolve                 : Terminates all active resources
"""
    print help_string
    exit(1)


#==================================================================================
#   Global initializations
#==================================================================================
configs, conn = cloud.init()
cloud.setup_keypair(configs,conn)
network       = cloud.setup_networking(configs,conn)
args          = sys.argv[1:]

if len(args) < 1 :
    help()
#==================================================================================
#   List all resources
#==================================================================================

if  args[0]  == "list_resources":
    cloud.list_resources(configs, conn)

#==================================================================================
#   List a particular resource by name
#==================================================================================

elif args[0] == "list_resource":
    if len(args) != 2:
        help()

    nodes = cloud.get_instances(configs, conn, {'tag:Name': args[1]})
    for node in nodes:
        print "{0:20} | {1:10} | {2:10} | {3:10}".format(node.tags['Name'],
                                                         node.id, node.ip_address, node.state)
    else:
        logging.error("{0} was not found".format(args[1]))

#==================================================================================
#   Start the headnode, this node will be the service node accessible to the world.
#   Will be setup with slurm and s3fs.
#==================================================================================

elif args[0] == "start_headnode":
    cloud.start_headnode(conn, network, configs, HEADNODE_NAME)

#==================================================================================
# Disassociate address and terminate the headnode.
#==================================================================================

elif args[0] == "stop_headnode":
    cloud.stop_node(configs, conn, [HEADNODE_NAME])

#==================================================================================
#   START WORKERS
#==================================================================================

elif args[0] == "start_workers":
    worker_count  = 1
    if len(args) >=  2 :
        worker_count = int(args[1])
    cloud.start_worker(conn, network, configs, worker_count)

#==================================================================================
# Disassiate address and terminate a specified number of nodes
#==================================================================================

elif args[0] == "stop_nodes":
    if len(args) >=  2 :
        worker_count = int(args[1])
        cloud.stop_nodes(configs, conn, network, worker_count)
    else:
        help()

#==================================================================================
# Disassiate address and terminate nodes by instance.id
#==================================================================================

elif args[0] == "stop_node":
    if len(args) >=  2 :
        worker_names = args[1:]
        cloud.stop_node(configs, conn, worker_names)
    else:
        help()
#==================================================================================
# Dissolve the entire setup. Removes the headnode and workers
#==================================================================================

elif args[0] == "dissolve":
    cloud.terminate_all_nodes(configs, conn)

#==================================================================================
# List all resources
#==================================================================================

elif args[0] == "list_resource":
    print("Not implemented")
    exit(-9);
    if len(args) !=  2 :
        help

    cloud.list_resource(driver, args[1])

#==================================================================================
# Invalid request
#==================================================================================

else:
    print "ERROR: Option ", args[0], " not recognized"
    help()
