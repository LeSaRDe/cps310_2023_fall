#!/bin/bash

read -p "Please specify the data space path: " ds_path
chown -R $USER:$USER /var/run/postgresql
export PGDATA=$ds_path
pg_ctl start -l $ds_path/logfile 


