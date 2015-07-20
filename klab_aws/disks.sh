#!/bin/bash

umount /mnt;
yes | mdadm --create --verbose /dev/md0 --level=stripe --raid-devices=2 /dev/xvdb /dev/xvdc;
mkfs.ext4 /dev/md0;
mount -t ext4 /dev/md0 /mnt ;
chmod -R 777 /mnt
