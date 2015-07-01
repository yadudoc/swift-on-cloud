#!/bin/bash

usage()
{
    echo $0: usage:
    cat <<EOF
    -s|--size)         The size of output file to be generated in Gb
    -o|--output)       The output file name
    -h|-?|--help)      Prints this help message
    *)                 The input files
EOF
}

while [ $# -gt 0 ]; do
  case $1 in
    -s|--size)         SIZE=$2         ;;
    -o|--output)       OUTFILE=$2      ;;
    -i|--inputs)       INPUTS=$2       ;;
    -h|-?|--help)      usage;exit      ;;
  esac
  shift 2
done

# If no count is defined set COUNT to 5
if [ -z $SIZE ] || [ "$SIZE" == "" ]
then
    SIZE=1
fi


echo "INPUTS : ${INPUTS[*]}"
echo "SIZE   : $SIZE Gb"
echo "OUTPUT : $OUTFILE"
