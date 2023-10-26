# Postgresql Demo

## 1. Download & Installation
Use the following link: https://www.postgresql.org/download/

## 2. Check if Postgresql is installed and running
- Check installation
    ```bash
    dpkg -l | grep postgres
    ```
    If it has been successfully installed, the output will look like this:
    ```
    ii  postgresql                                 16+255.pgdg22.04+1                      all          object-relational SQL database (supported version)
    ii  postgresql-16                              16.0-1.pgdg22.04+1                      amd64        The World's Most Advanced Open Source Relational Database
    ii  postgresql-client-16                       16.0-1.pgdg22.04+1                      amd64        front-end programs for PostgreSQL 16
    ii  postgresql-client-common                   255.pgdg22.04+1                         all          manager for multiple PostgreSQL client versions
    ii  postgresql-common                          255.pgdg22.04+1                         all          PostgreSQL database-cluster manager
    ```
- Check running
    ```bash
        sudo systemctl status postgresql
    ```
    If it is running, you may see the output of the cmd like this:
    ```
    postgresql.service - PostgreSQL RDBMS
        Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
        Active: active (exited) since Wed 2023-10-25 17:38:59 EDT; 1min 31s ago
    Main PID: 18449 (code=exited, status=0/SUCCESS)
            CPU: 1ms

    Oct 25 17:38:59 fmeng-p16 systemd[1]: Starting PostgreSQL RDBMS...
    Oct 25 17:38:59 fmeng-p16 systemd[1]: Finished PostgreSQL RDBMS.
    ```

Since we will manually start the Postgresql server, we do not need this system service running in the background. We stop this system service using the following cmd:
```bash
sudo systemctl stop postgresql
```
And, we disable it using the following cmd:
```bash
sudo systemctl disable postgresql
```
After this, Postgresql will not be started automatically in the start of OS.

## 3. Create a folder for the data of Postgresql
```bash
    cd ~/workspace
    mkdir postgres_data
```
The folder, `~/workspace/postgres_data`, thus is the place my Postgresql will store its data. 

> **NOTE**
> You may need to choose your own place to create this folder. 

## 4. Add Postgresql bin and lib to environment
If you are using Ubuntu, open the file, `.bashrc`, in your home folder, and append the following two lines to the end. Then save and quit.
```bash
    export PATH="$PATH:/usr/lib/postgresql/16/bin"
    export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/lib/postgresql/16/lib"
```
> **NOTE**
> The paths of `bin` and `lib` may vary in your system. If you couldn't find them in the folder `/usr/lib/postgresql`, using the cmd `whereis postgres` may give you some hints.

After the edit, logout your account, and login back. Then, open a terminal, and you should be able to use all related cmds of Postgresql now, e.g., `postgres`.

## 5. Initialize the data space of Postgresql
```bash
    initdb -D ~/workspace/postgres_data/
```
If it succeeds, the output will look like this:
```
The files belonging to this database system will be owned by user "fmeng".
This user must also own the server process.

The database cluster will be initialized with locale "en_US.UTF-8".
The default database encoding has accordingly been set to "UTF8".
The default text search configuration will be set to "english".

Data page checksums are disabled.

fixing permissions on existing directory /home/fmeng/workspace/postgres_data ... ok
creating subdirectories ... ok
selecting dynamic shared memory implementation ... posix
selecting default max_connections ... 100
selecting default shared_buffers ... 128MB
selecting default time zone ... America/New_York
creating configuration files ... ok
running bootstrap script ... ok
performing post-bootstrap initialization ... ok
syncing data to disk ... ok

initdb: warning: enabling "trust" authentication for local connections
initdb: hint: You can change this by editing pg_hba.conf or using the option -A, or --auth-local and --auth-host, the next time you run initdb.

Success. You can now start the database server using:

    pg_ctl -D /home/fmeng/workspace/postgres_data/ -l logfile start
```
> **NOTE** 
> The initialized data space is owned exclusively by the user account you used in the initialization. Pay particular attention to the line:
> `The files belonging to this database system will be owned by user "fmeng".`

## 6. Fix potential issues of Postgresql users
Theoretically, Postgresql has a default user, `postgres`. And, this user is required to exist in the OS. However, we never created this user, and we have created the data space for Postgresql under our own user account. In this case, when we try to start the Postgresql server, an error may occur. The error output looks like this:
```
(myenv_py310) fmeng@fmeng-p16:~/workspace$ postgres -D ~/workspace/postgres_data/
2023-10-25 18:07:42.510 EDT [20585] LOG:  starting PostgreSQL 16.0 (Ubuntu 16.0-1.pgdg22.04+1) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0, 64-bit
2023-10-25 18:07:42.510 EDT [20585] LOG:  listening on IPv4 address "127.0.0.1", port 5432
2023-10-25 18:07:42.517 EDT [20585] FATAL:  could not create lock file "/var/run/postgresql/.s.PGSQL.5432.lock": Permission denied
2023-10-25 18:07:42.520 EDT [20585] LOG:  database system is shut down
```
The line `FATAL:  could not create lock file "/var/run/postgresql/.s.PGSQL.5432.lock": Permission denied` explains this error clearly. And, when looking at this file, you may see the following:
```
(myenv_py310) fmeng@fmeng-p16: sudo ls -ahl /var/run
...
drwxrwsr-x  2 postgres          postgres   40 Oct 25 18:07 postgresql
...
```
This output shows that the `owner` and `group` of `/var/run/postgres` are `postgres` rather than my own OS user account `fmeng`. Thus, we need to change the `owner` and `group` of this folder and everything therein to `fmeng`. The following cmd helps do so:
```bash
sudo chown -R fmeng:fmeng /var/run/postgresql
```
After this cmd, the output will look like this:
```
(myenv_py310) fmeng@fmeng-p16: sudo ls -ahl /var/run
...
drwxrwsr-x  2 fmeng             fmeng    80 Oct 25 20:01 postgresql
...
```

## 7. Start Postgresql
The Postgresql server will be started upon the created data space, using the following cmd:
```bash
pg_ctl start -D /home/fmeng/workspace/postgres_data -l /home/fmeng/workspace/postgres_data/logfile
```
`-D` gives the data space folder, and `-l` gives the log file for the server. And, we do not have to create the log file beforehand.

If it succeeds, the output will look like this:
```
waiting for server to start.... done
server started
```

> **NOTE**
> `pg_ctl` will need the environment variable named `PGDATA` to be set to the data space path, if you do not want to use `-D` every time you use this cmd.

For convenience, we can create a Bash script, named `start_postgresql.sh`, with the following lines:
```bash
#!/bin/bash

read -p "Please specify the data space path: " ds_path
chown -R $USER:$USER /var/run/postgresql
export PGDATA=$ds_path
pg_ctl start -l $ds_path/logfile

```
Then, we enable the execution of this script as follows:
```bash
chmod +x start_postgresql.sh
```
This script does the following steps:
- (1) Ask for the data space path. And you will input that.
- (2) Change the `owner` and `group` of `/var/run/postgresql` to avoid the user issue.
- (3) Create the environment variable `PGDATA` for the data space path.
- (4) Start the Postgresql server.

To execute this script, you need to enter the folder where this script is located, and use the following cmd:
```bash
. start_postgresql.sh
```
> **NOTE**
> Please pay particular attention to the dot, `.`, at the beginning of this cmd. This dot will enable the envrionment variable `PGDATA` to be adopted by your terminal when you quit from the script. Otherwise, it will vanish after the script quits.

From now on, every time you want to start the Postgresql server, you will use this script to do it.

To check the status of the Postgresql server, using the following cmd:
```bash
pg_ctl status
```
And, the output will look like this:
```
pg_ctl: server is running (PID: 26712)
/usr/lib/postgresql/16/bin/postgres "-D" "/home/fmeng/workspace/postgres_data"
```

## 8. Stop Postgresql
To stop the server, we use the following cmd:
```bash
pg_ctl stop
```
And, the output will look like this:
```
waiting for server to shut down.... done
server stopped
```

## 9. Create a database
First of all, make sure your Postgresql server is running. The following cmd will help create a database in the server:
```bash
createdb my_db
```
You can choose your favorite name to replace `my_db`.

## 10. Connect to database from `psql`
`psql` is a client app for Postgresql. The following cmd helps connect to database:
```bash
psql my_db
```
If it succeeds, you will see a prompt shown in the terminal:
```
psql (16.0 (Ubuntu 16.0-1.pgdg22.04+1))
Type "help" for help.

my_db=#
```

## 11. User and password
To show users of the server, after connecting to the server, use the following cmd in the Postgresql console:
```bash
my_db=# \du+
                                    List of roles
 Role name |                         Attributes                         | Description 
-----------+------------------------------------------------------------+-------------
 fmeng     | Superuser, Create role, Create DB, Replication, Bypass RLS | 
```

In my server, I have only one user, `fmeng`.

To change the password of `fmeng`, use the following cmd:
```bash
my_db=# \password
Enter new password for user "fmeng": 
Enter it again: 
```

## 12. pgAdmin
`pgAdmin` is a graphic client of Postgresql. The following link points to the download and installation: https://www.pgadmin.org/download/

We can connect to the Postgresql server in `pgAdmin`, and we can operate the databases therein.

## 13. psycopg
`psycopg` is a 3<sup>rd</sup> party Python library for Postgresql. The following link points to the installation: https://www.psycopg.org/install/ It uses `pip` to install the library.
```bash
pip install psycopg
```