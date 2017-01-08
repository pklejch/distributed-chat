#!/bin/bash
if [ -z $1 ]
then
	target="$HOSTNAME"
else
	target="$1"
fi

. env/bin/activate

python -m distributed-chat cli ${HOSTNAME}:9999 -i ${target}:9999 -vv

deactivate
