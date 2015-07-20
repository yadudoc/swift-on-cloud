#!/usr/bin/env python

import os
import pprint
import ast

def _read_conf(config_file):
    cfile = open(config_file, 'r').read()
    config = {}
    for line in cfile.split('\n'):

        # Checking if empty line or comment
        if line.startswith('#') or not line :
            continue

        temp = line.split('=')
        config[temp[0]] = temp[1].strip('\r')
    return config

def pretty_configs(configs):
    printer = pprint.PrettyPrinter(indent=4)
    printer.pprint(configs)


def read_configs(config_file):
    config = _read_conf(config_file)

    if 'AWS_CREDENTIALS_FILE' in config :
        config['AWS_CREDENTIALS_FILE'] =  os.path.expanduser(config['AWS_CREDENTIALS_FILE'])
        config['AWS_CREDENTIALS_FILE'] =  os.path.expandvars(config['AWS_CREDENTIALS_FILE'])

        cred_lines    =  open(config['AWS_CREDENTIALS_FILE']).readlines()
        cred_details  =  cred_lines[1].split(',')
        credentials   = { 'AWS_Username'   : cred_details[0],
                          'AWSAccessKeyId' : cred_details[1],
                          'AWSSecretKey'   : cred_details[2] }
        config.update(credentials)
    else:
        print "AWS_CREDENTIALS_FILE , Missing"
        print "ERROR: Cannot proceed without access to AWS_CREDENTIALS_FILE"
        exit(-1)

    if 'WORKER_REQUEST' in config:
        try :
            config['WORKER_REQUEST']   = ast.literal_eval(config['WORKER_REQUEST'])
        except:
            print "Failed to parse WORKER_REQUEST: {0}".format(config['WORKER_REQUEST'])
            exit(-1)

    if 'AWS_DRY_RUN' in config and config['AWS_DRY_RUN'].lower() == 'true' :
        config['AWS_DRY_RUN'] = True
    else:
        config['AWS_DRY_RUN'] = False


    if 'AWS_KEYPAIR_FILE' in config:
        config['AWS_KEYPAIR_FILE'] = os.path.expanduser(config['AWS_KEYPAIR_FILE'])
        config['AWS_KEYPAIR_FILE'] = os.path.expandvars(config['AWS_KEYPAIR_FILE'])
    return config


HEADNODE_USERDATA_SLURM='''#!/bin/bash
cd /usr/local/bin
wget http://users.rcc.uchicago.edu/~yadunand/jdk-7u51-linux-x64.tar.gz; tar -xzf jdk-7u51-linux-x64.tar.gz;
wget http://users.rcc.uchicago.edu/~yadunand/swift-trunk-latest.tar.gz; tar -xzf swift-trunk-latest.tar.gz
export JAVA=/usr/local/bin/jdk1.7.0_51/bin
export SWIFT=/usr/local/bin/swift-trunk/bin
export PATH=$JAVA:$SWIFT:$PATH

apt-get update; apt-get install -y slurm-llnl jove python-pip python-boto
LOCAL=$(curl http://169.254.169.254/latest/meta-data/local-ipv4)
echo "$LOCAL headnode" > /etc/hosts

mkdir -p /etc/munge/     ; chmod 0700 /etc/munge
mkdir -p /var/lib/munge/ ; chmod 0711 /var/lib/munge
chmod 755 /var/log/
mkdir -p /var/log/munge/ ; chmod 0700 /var/log/munge
/usr/sbin/create-munge-key
rm -rf /var/run/munge
/etc/init.d/munge start

wget http://users.rcc.uchicago.edu/~yadunand/slurm.conf -O /etc/slurm-llnl/slurm.conf
wget http://users.rcc.uchicago.edu/~yadunand/nodelist -O /etc/slurm-llnl/nodelist

sed -i "s/ControlMachine=.*/ControlMachine=$HOSTNAME/g" /etc/slurm-llnl/nodelist
slurmctld
'''

WORKER_USERDATA_SLURM='''#!/bin/bash
apt-get update; apt-get -y install slurm-llnl jove
wget http://users.rcc.uchicago.edu/~yadunand/slurm.conf -O /etc/slurm-llnl/slurm.conf

echo "#ETC_LINE" >> /etc/hosts

echo "ControlMachine=swift-headnode\
NodeName=swift-worker-[1-32] State=FUTURE\
PartitionName=debug Nodes=swift-worker-[1-32] Default=YES MaxTime=INFINITE State=UP " > /etc/slurm-llnl/nodelist

$(/usr/bin/curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
'''

HEADNODE_USERDATA_TRUNK='''#!/bin/bash
WORKERPORT="50005"; SERVICEPORT="50010"
cd /usr/local/bin
wget http://users.rcc.uchicago.edu/~yadunand/jdk-7u51-linux-x64.tar.gz; tar -xzf jdk-7u51-linux-x64.tar.gz;
wget http://users.rcc.uchicago.edu/~yadunand/swift-trunk-latest.tar.gz; tar -xzf swift-trunk-latest.tar.gz
export JAVA=/usr/local/bin/jdk1.7.0_51/bin
export SWIFT=/usr/local/bin/swift-trunk/bin
export PATH=$JAVA:$SWIFT:$PATH
apt-get update; apt-get install -y build-essential git libfuse-dev libcurl4-openssl-dev libxml2-dev mime-support libtool mdadm
apt-get install -y automake
cd /home/ubuntu;
git clone https://github.com/yadudoc/cloud-tutorials.git
chmod 777 cloud-tutorials
git clone https://github.com/s3fs-fuse/s3fs-fuse
cd s3fs-fuse/
./autogen.sh
./configure --prefix=/usr
make && make install
mkdir /scratch;
mdadm --create --verbose /dev/md0 --level=stripe --raid-devices=2 /dev/xvdb /dev/xvdc
mkfs.ext4 /dev/md0; mount -t ext4 /dev/md0 /scratch; chmod 777 /scratch
mkdir /s3; chmod 777 /s3;

coaster_loop ()
{
    while :
    do
        coaster-service -p $SERVICEPORT -localport $WORKERPORT -nosec -passive &> /var/log/coaster-service.logs
        sleep 10;
    done
}
coaster_loop &
'''

WORKER_USERDATA_TRUNK='''#!/bin/bash
#Replace_me
HEADNODE=SET_HEADNODE_IP
CONCURRENCY="SET_CONCURRENCY"
#WORKER_INIT_SCRIPT
WORKERPORT="50005"
#Ping timeout
cd /home/ubuntu
apt-get update; apt-get install -y build-essential git libfuse-dev libcurl4-openssl-dev libxml2-dev mime-support libtool mdadm
install_s3fs() {
   apt-get install -y automake
   git clone https://github.com/s3fs-fuse/s3fs-fuse
   cd s3fs-fuse/ ; ./autogen.sh; ./configure --prefix=/usr
   make; sudo make install
}; #install_s3fs;
cd /usr/local/bin
wget http://users.rcc.uchicago.edu/~yadunand/jdk-7u51-linux-x64.tar.gz; tar -xzf jdk-7u51-linux-x64.tar.gz;
wget http://users.rcc.uchicago.edu/~yadunand/swift-trunk-latest.tar.gz; tar -xzf swift-trunk-latest.tar.gz
#wget http://users.rcc.uchicago.edu/~yadunand/docker_run -O /usr/local/bin/swift-trunk/bin/docker_run
chmod a+x /usr/local/bin/swift-trunk/bin/docker_run
export JAVA=/usr/local/bin/jdk1.7.0_51/bin
export SWIFT=/usr/local/bin/swift-trunk/bin
export PATH=$JAVA:$SWIFT:$PATH
disks() {
   umount /mnt;
   yes | mdadm --create --verbose /dev/md0 --level=stripe --raid-devices=2 /dev/xvdb /dev/xvdc;
   mkfs.ext4 /dev/md0; mount -t ext4 /dev/md0 /mnt ; chmod -R 777 /mnt
}; disks;
mkdir /s3; chmod 777 /s3;
PTIMEOUT=4
#Disk_setup
export SWIFT=/usr/local/bin/swift-trunk/bin
export PATH=$JAVA:$SWIFT:$PATH
export ENABLE_WORKER_LOGGING
export WORKER_LOGGING_LEVEL=DEBUG
worker_loop ()
{
    while :
    do
        echo "Connecting to HEADNODE on $HEADNODE"
        worker.pl -w 3600 $CONCURRENCY http://$HEADNODE:$WORKERPORT $HOSTNAME /var/log/worker-$HOSTNAME.log
        sleep 5
    done
}
worker_loop &
'''

def getstring(target):
    if target == "headnode_coasters":
        return HEADNODE_USERDATA_TRUNK

    elif target == "worker_coasters":
        return WORKER_USERDATA_TRUNK

    elif target == "headnode_slurm":
        return HEADNODE_USERDATA_SLURM

    elif target == "worker_slurm":
        return WORKER_USERDATA_SLURM

    else:
        return -1
