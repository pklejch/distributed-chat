#!/bin/bash
if [ -z $1 ]
then
	$1="$HOSTNAME"
fi

. env/bin/activate

python -m distributed-chat cli ${HOSTNAME}:9999 -i ${1}:9999
