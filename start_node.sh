#!/bin/bash

. env/bin/activate

if [ -z $1 ]
then
	python -m distributed-chat cli ${HOSTNAME}:9999 -vv
else
	python -m distributed-chat cli ${HOSTNAME}:9999 -i ${1}:9999 -vv
fi



deactivate
