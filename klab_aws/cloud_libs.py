#!/usr/bin/env python
# References :  https://github.com/tomcz/aws_vpc_py/blob/master/aws.py
# This reference uses an MIT like licence with the only requirement being that the
# original copyright notice is included.

import datetime
import time
import configurator
import os
import logging
import sys
import json
import urllib2
import ast

import imp
try:
    imp.find_module('boto')
except ImportError:
    sys.stderr.write("Python: Apache libcloud module not available, cannot proceed\n")
    exit(-1)

import boto
import boto.ec2


#==================================================================================
# Global defs
#==================================================================================
HEADNODE_NAME="swift-headnode"
ERR_CODE={'HEADNODE_NO_IP': 5,
          'HEADNODE_NO_EXIST': 6,
          'CONFIG_SANITY_FAIL': 2}
#==================================================================================

def get_on_demand_prices(driver, configs):
    instance_url = "http://aws.amazon.com/ec2/pricing/pricing-on-demand-instances.json"
    response     = urllib2.urlopen(instance_url)
    pricing      = json.loads(response.read())
    reg_pricing  = pricing['config']['regions']

    Prices       = {}
    for region in reg_pricing:
        if region['region'] in configs['AWS_REGION']:
            for instType in region["instanceTypes"]:
                for size in instType['sizes']:
                    Prices[size['size']] = [ size['valueColumns'][0]['prices']['USD'] ]
                    #print size['size'], size['valueColumns'][0]['prices']['USD']

    return Prices

def get_public_ip(driver, name):
    print "Not implemented"

def aws_create_security_group(driver, configs):
    print "Not implemented"

def check_keypair(driver, configs):
    print "Not implemented"

def terminate_node(driver, node_names):
    print "No worker_disk defined"

def help():
    print "No worker_disk defined"

def filter_by_name(function, name):
    filters = {'tag:Name': name}
    return function(filters=filters)

def filter_by_name_and_vpc(function, name, vpc):
    filters = {'tag:Name': name, 'vpc-id':vpc.id}
    return function(filters=filters)

def setup_vpc(conn, vpc_name, cidr_block):
    # Check if a vpc named vpc_name already exists
    for vpc in filter_by_name(conn.get_all_vpcs, vpc_name):
        logging.debug("found existing vpc with matching name :", vpc)
        return vpc
    # VPC does not exist, we should create it.
    vpc = conn.create_vpc(cidr_block, instance_tenancy='default')
    vpc.add_tag('Name', vpc_name)
    logging.debug("Created new vpc :", vpc)
    return vpc


def setup_gateway(conn, vpc, vpc_name):
    logging.debug("Setting up gateway")
    # If gateway exists, return that
    for gateway in filter_by_name(conn.get_all_internet_gateways, vpc_name):
        return gateway
    # Create new gateway if none exists
    gateway = conn.create_internet_gateway()
    # Tag gateway with vpc_name for simplicity
    gateway.add_tag('Name', vpc_name);
    conn.attach_internet_gateway(gateway.id, vpc.id)
    logging.debug("Created gateway : ", gateway)
    return gateway


def setup_routetable(conn, vpc, route_name, gateway, dest_cidr_block):
    logging.debug("setup_routetable : Setting up routetable")
    # If route_table exists, return that
    for route_table in filter_by_name_and_vpc(conn.get_all_route_tables, route_name, vpc):
        logging.debug("setup_routetable : Found route table, Skipping create")
        logging.debug("setup_routetable : Route_table : ", route_table)
        return route_table

    # Create new route_table if none exists
    route_table = conn.create_route_table(vpc.id)
    # Tag gateway with vpc_name for simplicity
    route_table.add_tag('Name', route_name);

    logging.debug("Setting up route for access from anywhere")
    conn.create_route(route_table.id, dest_cidr_block, gateway.id)
    return route_table


'''
Setup subnets which isolate, workers which are protected and services
which need to be accessible and act as bridges to reach workers.
'''
def setup_subnet(conn, vpc, route_table, subnet_name, cidr_block, region):

    zones = conn.get_all_zones()
    if not zones:
        logging.error("Unable to find zones under region:{0}".region)
        exit(-1)
    zone = zones[0];

    for subnet in filter_by_name_and_vpc(conn.get_all_subnets, subnet_name, vpc):
        logging.debug("Found subnet : ", subnet)
        return subnet

    logging.debug("Creating a subnet : ", subnet_name)
    try:
        subnet = conn.create_subnet(vpc.id, cidr_block, zone.name)

    except boto.exception.EC2ResponseError as err:
        logging.error("Failed to create subnet : {0}".format(err))
        exit(-1)

    subnet.add_tag('Name', subnet_name)
    logging.debug("Associating subnet with route_table ")
    conn.associate_route_table(route_table.id, subnet.id)
    return subnet


# Note that setup_security_group takes boto.ec2.connection rather
# than a connection to the vpc region
def setup_security_group (conn, vpc, group_name):
    for secgroup in conn.get_all_security_groups(filters={'group-name': group_name}):
        if secgroup.vpc_id == vpc.id :
            logging.debug("Found security group belonging to VPC")
            logging.debug(secgroup.rules)
            return secgroup

    logging.debug("Creating new security group : ", group_name)
    secgroup = conn.create_security_group(group_name, group_name, vpc.id)
    secgroup.authorize(ip_protocol='tcp', from_port=0,  to_port=65000, cidr_ip='0.0.0.0/0')
    secgroup.authorize(ip_protocol='udp', from_port=0,  to_port=65000, cidr_ip='0.0.0.0/0')

    return secgroup



def setup_networking(configs, conn):
    """
    AWS docs : http://docs.aws.amazon.com/AmazonVPC/latest/GettingStartedGuide/ExerciseOverview.html
    boto docs: http://boto.readthedocs.org/en/latest/vpc_tut.html
    """
    configs['vpc_name']        = 'swift_vpc'
    configs['table_name']      = 'Swift_route_table'
    configs['dest_cidr_block'] = '0.0.0.0/0'
    configs['worker_net']      = 'worker-subnet'
    configs['service_net']     = 'service-subnet'
    configs['VPC_block']       = '42.43.0.0/16'
    configs['service_block']   = '42.43.128.0/28'
    configs['worker_block']    = '42.43.0.0/17'

    vpc_name        = configs['vpc_name']
    table_name      = configs['table_name']
    dest_cidr_block = configs['dest_cidr_block']
    worker_net      = configs['worker_net']
    service_net     = configs['service_net']
    VPC_block       = configs['VPC_block']
    service_block   = configs['service_block'] # Supports 128 individual nodes ranging from 42.0.0.0 -> 42.0.0.127
    worker_block    = configs['worker_block']  # Support 65536 individual nodes which is probably more than suffiient.


    regions    = boto.ec2.regions()
    [region]   = [ r for r in regions if r.name == configs['AWS_REGION'] ]

    '''
    for vpc in filter_by_name(conn.vpc.get_all_vpcs, vpc_name):
        print vpc

    exit
    '''

    from boto.vpc import VPCConnection
    vconn = VPCConnection(aws_access_key_id=configs['AWSAccessKeyId'],
                          aws_secret_access_key=configs['AWSSecretKey'],
                          region=region)

    # Setup VPC
    vpc     = setup_vpc(vconn, vpc_name, VPC_block)

    # Setup internet_gateway
    gateway = setup_gateway(vconn, vpc, vpc_name)

    # Setup route_table
    route_table = setup_routetable(vconn, vpc, table_name, gateway, dest_cidr_block)

    # Setup one subnet for the services, and one subnet for the workers
    worker_subnet  = setup_subnet(vconn, vpc, route_table, worker_net,  worker_block, configs['AWS_REGION'])
    configs['worker_subnet_id'] = worker_subnet.id
    service_subnet = setup_subnet(vconn, vpc, route_table, service_net, service_block, configs['AWS_REGION'])
    configs['service_subnet_id'] = service_subnet.id
    worker_sec = setup_security_group(conn, vpc, "worker_security_group")
    service_sec = setup_security_group(conn, vpc, "service_security_group")

    logging.debug("[VPC]  Name       : ", vpc_name)
    logging.debug("[VPC]  id         : ", vpc.id)
    logging.debug("[VPC]  cidr block : ", vpc.cidr_block)

    network = { 'VPC'              : vpc,
                'GATEWAY'          : gateway,
                'ROUTE_TABLE'      : route_table,
                'WORKER_SUBNET'    : worker_subnet,
                'SERVICE_SUBNET'   : service_subnet,
                'WORKER_SECGROUP'  : worker_sec,
                'SERVICE_SECGROUP' : service_sec
               }
    return network

def setup_headnode_userdata(configs):

    if configs['SERVICE_TYPE'] == 'slurm':
        userdata = configurator.getstring("headnode_slurm")
    elif configs['SERVICE_TYPE'] == 'coasters':
        userdata = configurator.getstring("headnode_coasters")
    else:
        logging.error("Unknown SERVICE_TYPE:{0}\nCannot proceed, failing".format(configs['SERVICE_TYPE']))
        exit(-1);

    return userdata

def start_headnode(conn, network, configs, instance_name):

    # Start headnode only if one does not exist.
    nodes = get_instances(configs, conn, {'tag:Name': HEADNODE_NAME})
    for node in nodes:
        if node.state == 'running':
            logging.warn("Attempting to start headnode while one exists {0} | {1}".format(nodes[0].tag['Name'], nodes[0].ip_address))
            return node

    print "[DEBUG] start_headnode : {0}".format(instance_name)
    userdata    = setup_headnode_userdata(configs)

    reservation = conn.run_instances(configs['HEADNODE_IMAGE'],
                                     min_count=1,
                                     max_count=1,
                                     instance_type=configs['HEADNODE_MACHINE_TYPE'],
                                     security_group_ids=[network['SERVICE_SECGROUP'].id],
                                     key_name=configs['AWS_KEYPAIR_NAME'],
                                     subnet_id=network['SERVICE_SUBNET'].id,
                                     user_data=userdata)

    idx = 0
    for instance in reservation.instances:
        print instance, instance.id
        sleep_until(instance, 'running')
        instance.add_tag('Name', instance_name)
        address = setup_elastic_ip(conn)
        conn.associate_address(instance_id=instance.id, allocation_id=address.allocation_id)
        idx += 1

    return reservation.instances

def setup_worker_userdata(configs, headnode_ip):

    if configs['SERVICE_TYPE'] == 'slurm':
        userdata = configurator.getstring("worker_slurm")
    elif configs['SERVICE_TYPE'] == 'coasters':
        userdata = configurator.getstring("worker_coasters")
    else:
        logging.error("Unknown SERVICE_TYPE:{0}\nCannot proceed, failing".format(configs['SERVICE_TYPE']))
        exit(-1);

    userdata   = userdata.replace("SET_HEADNODE_IP", headnode_ip)
    concurrency= ""
    if 'WORKER_CONCURRENCY' in configs:
        concurrency = "-c " + str(configs['WORKER_CONCURRENCY'])
    userdata    = userdata.replace("SET_CONCURRENCY", concurrency)

    if 'WORKER_INIT_SCRIPT' in configs :
        if not os.path.isfile(configs['WORKER_INIT_SCRIPT']):
            print "Unable to read WORKER_INIT_SCRIPT"
            exit(-1);
        init_string = open(configs['WORKER_INIT_SCRIPT'], 'r').read()
        userdata    = userdata.replace("#WORKER_INIT_SCRIPT", init_string)

    logging.info("Worker userdata : %s", userdata)

    userdata = userdata.replace("#ETC_LINE", "{0}\t{1}".format(headnode_ip, HEADNODE_NAME))
    logging.debug("USERDATA:\n{0}\n".format(userdata))

    return userdata

def start_worker(conn, network, configs, count):

    print "DEBUG: start_worker : ",count
    nodes = get_instances(configs, conn, {'tag:Name': HEADNODE_NAME})
    if not nodes:
        logging.error("HEADNODE is not online :{0}".format(HEADNODE_NAME))
        logging.error("FATAL! Cannot proceed. Dying.")
        exit(ERR_CODE['HEADNODE_NO_EXIST'])

    headnode_ip = nodes[0].ip_address
    if not headnode_ip:
        logging.error("{0} is not associated with a public_ip_address".format(HEADNODE_NAME))
        logging.error("FATAL! Cannot proceed. Dying.")
        exit(ERR_CODE['HEADNODE_NO_IP'])

    userdata   = setup_worker_userdata(configs, headnode_ip)
    reservation = conn.run_instances(configs['WORKER_IMAGE'],
                                     min_count=1,
                                     max_count=count,
                                     instance_type=configs['WORKER_MACHINE_TYPE'],
                                     security_group_ids=[network['WORKER_SECGROUP'].id],
                                     key_name=configs['AWS_KEYPAIR_NAME'],
                                     subnet_id=network['WORKER_SUBNET'].id,
                                     user_data=userdata)

    idx = 0
    for instance in reservation.instances:
        instance.add_tag('Name', "sworker-{0}".format(instance.id))
        instance.add_tag('subnet_id', network['WORKER_SUBNET'])
        sleep_until(instance, 'running')
        address = setup_elastic_ip(conn)
        conn.associate_address(instance_id=instance.id, allocation_id=address.allocation_id)
        idx += 1

    return reservation.instances


def check_conf_sanity(configs):
    if configs["SERVICE_TYPE"] not in ["coasters", "slurm"]:
        logging.error("Unknown SERVICE_TYPE : {0}".format(configs["SERVICE_TYPE"]))
        logging.error("Failing. Cannot process ")
        exit(ERR_CODE['CONFIG_SANITY_FAIL'])

    logging.debug("CONFIG sanity checks pass")


def init():
    logging.basicConfig(filename='aws.log', level=logging.INFO, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

    configs    = configurator.read_configs('configs')

    regions    = boto.ec2.regions()
    check_conf_sanity(configs)

    logging.debug("AWS region : ", configs['AWS_REGION'])
    if configs['AWS_REGION'] not in [x.name for x in regions]:
        print configs['AWS_REGION']

    conn       = boto.ec2.connect_to_region(configs['AWS_REGION'],
                                            aws_access_key_id=configs['AWSAccessKeyId'],
                                            aws_secret_access_key=configs['AWSSecretKey'])
    if conn == None :
        print "[INFO] : Region name could be incorrect"
        print "[ERROR]: Failed to connect to region, exiting"
        exit(-1)

    configs['AWS_KEYPAIR_NAME'] = configs['AWS_KEYPAIR_NAME'] + "." + configs['AWS_REGION']
    return configs, conn

# Keypairs will be handled differently by boto.
# If keypair is present return.
# Keypair for multiple regions will be stored in the folder.
#
def setup_keypair(configs, conn):
    if not os.path.isdir(configs['AWS_KEYPAIR_DIR']):
        os.makedirs(configs['AWS_KEYPAIR_DIR'])

    aws_keypair = conn.get_key_pair(configs['AWS_KEYPAIR_NAME'])
    keyfile     = configs['AWS_KEYPAIR_DIR'] + "/" + configs['AWS_KEYPAIR_NAME']+".pem"

    if aws_keypair and os.path.exists(keyfile):
        logging.debug("{0} exists.".format(aws_keypair))
        return

    else:
        # Eith the keypair or keyfile does not exist.
        print "Removing keypair and/or local keyfile"
        if aws_keypair:
            print "Deleted the keypair"
            aws_keypair.delete()

        if os.path.exists(keyfile):
            print "Deleting local keyfile"
            os.remove(keyfile)

    print "AWS_KEYPAIR unavailable in region."
    # If the keypair file location exists, then the new keypair file
    # must not overwrite it. The user must specify a new location
    print "Attempting to create keypair : ", configs['AWS_KEYPAIR_NAME']
    key_pair = conn.create_key_pair(configs['AWS_KEYPAIR_NAME'])
    print "Create keypair:{0} ".format(configs['AWS_KEYPAIR_NAME'])
    key_pair.save(configs['AWS_KEYPAIR_DIR'])
    print "Create local keyfile:{0} ".format(keyfile)


# This func returns an unattached elastic ip address
def setup_elastic_ip(conn):
    #If there is an unattached ip address return that.
    #Else create a new ip
    for address in conn.get_all_addresses(filters={'domain':'vpc'}):
        if not address.instance_id:
            return address
    print "No free elastic ip. Creating new one"
    address = conn.allocate_address(domain="vpc")
    return address


def launch_instance_into_subnet(conn, network, instance_type, configs, instance_names):
    print "launch_instance_into_subnet"

    if len(instance_names) == 0:
        return []

    print "Instance type :{0}".format(instance_type)

    reservation = conn.run_instances(configs['WORKER_IMAGE'],
                                     min_count=len(instance_names),
                                     max_count=len(instance_names),
                                     instance_type=configs['WORKER_MACHINE_TYPE'],
                                     security_group_ids=[network['WORKER_SECGROUP'].id],
                                     key_name=configs['AWS_KEYPAIR_NAME'],
                                     subnet_id=network['WORKER_SUBNET'].id)
    #user_data=)
    idx = 0
    for instance in reservation.instances:
        print instance
        sleep_until(instance, 'running')
        # TODO : FIX .BUG HERE
        instance.add_tag('Name', instance_names[idx])
        address = setup_elastic_ip(conn)
        conn.associate_address(instance_id=instance.id, allocation_id=address.allocation_id)
        idx += 1

    return reservation.instances

def sleep_until(instance, state):
    instance.update()
    while instance.state != state:
        print "Waiting for instance[{0}:{1}]".format(instance.id, instance.state)
        time.sleep(2)
        instance.update()

def get_instances(configs, conn, filters):
    nodes = []
    for reservation in conn.get_all_instances(filters=filters):
        nodes.extend(reservation.instances)
        for instance in reservation.instances:
            logging.debug("Instance:{0} State:{1} Subnet:{2} IP_addr:{3}".format(instance.id, instance.state, instance.subnet_id, instance.ip_address))
    return nodes

def list_resources(configs, conn):

    #filters = {'tag:Name': name, 'vpc-id':vpc.id}
    #return function(filters=filters)
    service_nodes  = get_instances(configs, conn, {'subnet-id': configs['service_subnet_id']})
    worker_nodes   = get_instances(configs, conn, {'subnet-id': configs['worker_subnet_id' ]})
    print "======================SERVICE SUBNET============================="
    print "{0:20} | {1:10} | {2:10} | {3:10}".format("Name","ID", "IP_Addr", "State")
    for node in service_nodes:
        if 'Name' in node.tags :
            print "{0:20} | {1:10} | {2:10} | {3:10}".format(node.tags['Name'],
                                                             node.id, node.ip_address, node.state)
        else:
            print "{0:20} | {1:10} | {2:10} | {3:10}".format("-",
                                                             node.id, node.ip_address, node.state)
    print "======================WORKER SUBNET=============================="
    print "{0:20} | {1:10} | {2:10} | {3:10}".format("Name","ID", "IP_Addr", "State")
    for node in worker_nodes:
        if 'Name' in node.tags :
            print "{0:20} | {1:10} | {2:10} | {3:10}".format(node.tags['Name'],
                                                             node.id, node.ip_address, node.state)
        else:
            print "{0:20} | {1:10} | {2:10} | {3:10}".format("-",
                                                             node.id, node.ip_address, node.state)


def manage_ip(configs, conn, instances):

    for instance in instances:
        logging.debug("getting elastic ip for instance: ", instance.id)
        setup_elastic_ip(conn)
        associate_elastic_ip(conn,instance)
    return


def terminate_instance(configs, conn, instance_id ):
    node = get_instances(configs, conn, {'instance-id': instance_id})
    print node
    print node[0].id
    addrs = [address for address in conn.get_all_addresses(filters={'instance-id': [node[0].id]})]
    for address in addrs:
        print "DEBUG: Disassociating address: {0} from {1}".format(address, node.id)
        address.disassociate(dry_run=configs['AWS_DRY_RUN'])
    node[0].terminate(dry_run=configs['AWS_DRY_RUN'])

def terminate_all_nodes(configs, conn):
    service_nodes  = get_instances(configs, conn, {'subnet-id': configs['service_subnet_id']})
    worker_nodes   = get_instances(configs, conn, {'subnet-id': configs['worker_subnet_id' ]})
    nodes          = [node.tags['Name'] for node in service_nodes + worker_nodes]
    stop_node(configs, conn, nodes)


def stop_node(configs, conn, node_names):
    nodes = get_instances(configs, conn, {'tag:Name': node_names})
    for node in nodes:
        addrs = [address for address in conn.get_all_addresses(filters={'instance-id': [node.id]})]
        for address in addrs:
            print "DEBUG: Disassociating address: {0} from {1}".format(address, node.id)
            address.disassociate()
        node.terminate()


def stop_nodes(configs, conn, network, worker_count):
    logging.debug("Stopping nodes: {0}".format(worker_count))
    nodes = get_instances(configs, conn, {'subnet-id': configs['worker_subnet_id']})
    logging.debug("nodes: {0}".format(nodes))
    for node in nodes[0:worker_count]:
        print "[DEBUG] : Deleting node : {0}:{1}".format(node.id, node.tags['Name'])
        addrs = [address for address in conn.get_all_addresses(filters={'instance-id': [node.id]})]
        for address in addrs:
            print "DEBUG: Disassociating address: {0} from {1}".format(address, node.id)
            address.disassociate()
        node.terminate()

def process_price(request):
    request = ast.literal_eval(request)
    if request['type'].lower() == "spot" :
        print "Requesting a spot instance at {0}".format(float(request['price']))
        return float(request['price'])


def spot_request_submit(conn, network, configs, count):
    print "DEBUG: start_worker : ",count
    nodes = get_instances(configs, conn, {'tag:Name': HEADNODE_NAME})
    if not nodes:
        logging.error("HEADNODE is not online :{0}".format(HEADNODE_NAME))
        logging.error("FATAL! Cannot proceed. Dying.")
        exit(ERR_CODE['HEADNODE_NO_EXIST'])

    headnode_ip = nodes[0].ip_address
    if not headnode_ip:
        logging.error("{0} is not associated with a public_ip_address".format(HEADNODE_NAME))
        logging.error("FATAL! Cannot proceed. Dying.")
        exit(ERR_CODE['HEADNODE_NO_IP'])

    userdata    = setup_worker_userdata(configs, headnode_ip)

    price       = process_price(configs['WORKER_REQUEST'])

    spot_reqs   = conn.request_spot_instances(price,
                                              configs['WORKER_IMAGE'],
                                              count=count,
                                              instance_type=configs['WORKER_MACHINE_TYPE'],
                                              type='one-time',
                                              security_group_ids=[network['WORKER_SECGROUP'].id],
                                              key_name=configs['AWS_KEYPAIR_NAME'],
                                              subnet_id=network['WORKER_SUBNET'].id,
                                              user_data=userdata,
                                              dry_run=configs['AWS_DRY_RUN'])

    time.sleep(10)
    print "Spot_requests : {0}".format(spot_reqs)
    request_ids  = [x.id for x in spot_reqs]
    idx = 0
    flag = True
    instances = []
    while flag:
        flag = False
        requests = conn.get_all_spot_instance_requests(request_ids=request_ids)
        for req in requests:
            print "Req_id:{0} Req_state:{1} Req_status:{2} Req_instance:{3} ".format(req.id,
                                                                                    req.state,
                                                                                    req.status,
                                                                                    req.instance_id)
            if req.instance_id == None:
                flag = True
        time.sleep(15)

    requests = conn.get_all_spot_instance_requests(request_ids=request_ids)
    instance_ids = [ x.instance_id for x in requests ]
    print "Instance ids : ", instance_ids

    instances= get_instances(configs, conn, {'instance-id': instance_ids })

    for instance in instances:
        instance.add_tag('Name', "sworker-{0}".format(instance.id))
        instance.add_tag('subnet_id', network['WORKER_SUBNET'])


    for instance in instances:
        sleep_until(instance, 'running')
        address = setup_elastic_ip(conn)
        conn.associate_address(instance_id=instance.id, allocation_id=address.allocation_id)
        idx += 1

    return instances
