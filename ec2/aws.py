#!/usr/bin/env python
# References :  https://github.com/tomcz/aws_vpc_py/blob/master/aws.py
# This reference uses an MIT like licence with the only requirement being that the
# original copyright notice is included.

import datetime
import time
import configurator
import cloud_libs as cloud
import cloud_spotting as spots
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
    price_lookup             : Generates a table of spot prices and on-demand prices for the region
    spot_request_submit      : Submit a spot request for worker nodes.
    spot_request_status      : Shows status of all outstanding spot requests
    spot_request_cancel      : [TODO] Cancel an outstanding spot request

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
#   Display table of On-demand vs Spot prices for all instances within region
#   specified via configs
#==================================================================================

elif args[0] == "price_lookup":
    od_prices = cloud.get_on_demand_prices(conn, configs)
    sp_prices = spots.get_spot_prices(conn, configs)

    print "{0:15} {1:10} {2:10} {3:15}".format("Instance Type", "On-demand", "Spot price", "Region")
    for key in od_prices:
        if key in sp_prices:
            print "{0:15} {1:10} {2:10} {3:15}".format(key, od_prices[key][0], sp_prices[key][0].price, sp_prices[key][0].region)
        else:
            print "{0:15} {1:10} {2:>10} {3:>15}".format(key, od_prices[key][0], "NA", "NA")

#==================================================================================
#   Spot instance tests
#
#==================================================================================

elif args[0] == "plot_spot_prices":
    price_hist = spots.get_spot_prices(conn, configs)

elif args[0] == "spot_request_submit":
    count = 2
    foo   = cloud.spot_request_submit(conn, network, configs, count)
    print foo

elif args[0] == "spot_request_status":
    requests = conn.get_all_spot_instance_requests()
    print "{0:15} {1:10} {2:10} {3:10} {4:5}".format("Req_ID" , "State", "Status", "Instance-id", "Price")
    for request in requests:
        print "{0:15} {1:10} {2:10} {3:10} {4:5}".format(request.id , request.state, request.status, request.instance_id, request.price)

elif args[0] == "spot_request_cancel":
    requests = conn.get_all_spot_instance_requests()
    r_ids    = [ r.id for r in requests]
    print "r_ids : {0}".format(r_ids)
    print conn.cancel_spot_instance_requests(r_ids, dry_run=configs['AWS_DRY_RUN'])

elif args[0] == "terminate_instance":
    if len(args) >=  2 :
        instance_id = args[1]
        print "instance_id : {0}".format(instance_id)
        cloud.terminate_instance(configs, conn, instance_id);
    else:
        help()


#==================================================================================
# Invalid request
#==================================================================================

else:
    print "ERROR: Option ", args[0], " not recognized"
    help()
