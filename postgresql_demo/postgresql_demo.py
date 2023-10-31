import logging
import time
import multiprocessing as mp
import psycopg


HOSTNAME= 'localhost'
DBNAME = 'my_db'
USER = 'fmeng'
PASSWORD = ''


def create_table():
    """
    Create a table in DB.
    """
    logging.debug('[create_table] Starts.')
    # Connect to DB.
    # with psycopg.connect('dbname=%s user=%s password=%s' % (DB_NAME, USER_NAME, PASSWORD)) as db_con:
    with psycopg.connect(host=HOSTNAME, dbname=DBNAME, user=USER, password=PASSWORD) as db_con:
        # Open a cursor to perform DB operations
        with db_con.cursor() as db_cur:
            # Compose a SQL cmd for creating the table.
            # About 'CREATE TABLE': https://www.postgresql.org/docs/current/sql-createtable.html
            # Data types supported by Postgresql: https://www.postgresql.org/docs/current/datatype-numeric.html
            # About primary key: https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-PRIMARY-KEYS
            sql_str = """create table if not exists human_status (
                                tick serial,
                                aid serial,
                                state smallserial,
                                energy integer,
                                primary key (tick, aid)
                                )
                       """
            # Execute the SQL cmd.
            db_cur.execute(sql_str)
    logging.debug('[create_table] Done.')


def insert_data_rec():
    logging.debug('[insert_data_rec] Starts.')
    tbl_name = 'human_status'
    tick = 1
    aid = 2
    state = 2
    energy = 95
    with psycopg.connect(host=HOSTNAME, dbname=DBNAME, user=USER, password=PASSWORD) as db_con:
        with db_con.cursor() as db_cur:
            sql_str = """insert into %s (tick, aid, state, energy) values (%s, %s, %s, %s)
                      """ % (tbl_name, tick, aid, state, energy)
            db_cur.execute(sql_str)
        db_con.commit()
    logging.debug('[insert_data_rec] Done.')


def fetch_data_rec():
    logging.debug('[insert_data_rec] Starts.')
    tbl_name = 'human_status'
    state = 2
    with psycopg.connect(host=HOSTNAME, dbname=DBNAME, user=USER, password=PASSWORD) as db_con:
        with db_con.cursor() as db_cur:
            sql_str = """select * from %s where state=%s
                      """ % (tbl_name, state)
            db_cur.execute(sql_str)
            data_idx = 0
            while True:
                data_rec = db_cur.fetchone()
                if data_rec is None:
                    break
                logging.debug('[fetch_data_rec] data rec %s: tick=%s, aid=%s, state=%s, energy=%s'
                              % (data_idx, data_rec[0], data_rec[1], data_rec[2], data_rec[3]))
                data_idx += 1
    logging.debug('[insert_data_rec] Starts.')


def row_lock_test():
    logging.debug('[row_lock_test] Starts.')
    tbl_name = 'human_status'
    max_iter = 10000

    def row_read_func(tid, aid):
        iter_idx = 0
        with psycopg.connect(host=HOSTNAME, dbname=DBNAME, user=USER, password=PASSWORD) as db_con:
            with db_con.cursor() as db_cur:
                while True:
                    if iter_idx >= max_iter:
                        break
                    if aid == 1:
                        sql_str = """select * from %s where aid=%s for update""" % (tbl_name, aid)
                    else:
                        sql_str = """select * from %s where aid=%s""" % (tbl_name, aid)
                    db_cur.execute(sql_str)
                    while True:
                        data_rec = db_cur.fetchone()
                        if data_rec is None:
                            break
                        logging.debug('[row_read_func: %s] iter %s: tick=%s, aid=%s, state=%s, energy=%s'
                                      % (tid, iter_idx, data_rec[0], data_rec[1], data_rec[2], data_rec[3]))
                    iter_idx += 1
                    # time.sleep(1)

    def row_write_func(tid, aid):
        iter_idx = 0
        energy = 1
        with psycopg.connect(host=HOSTNAME, dbname=DBNAME, user=USER, password=PASSWORD) as db_con:
            with db_con.cursor() as db_cur:
                while True:
                    if iter_idx >= max_iter:
                        break
                    sql_str = """update %s set energy=%s where aid=%s""" % (tbl_name, energy, aid)
                    db_cur.execute(sql_str)
                    db_con.commit()
                    logging.debug('[row_write_func: %s] iter %s: energy=%s'
                                  % (tid, iter_idx, energy))
                    energy += 1
                    iter_idx += 1

    write_proc_1 = mp.Process(target=row_write_func, args=(1, 1))
    write_proc_2 = mp.Process(target=row_write_func, args=(2, 2))
    read_proc_1 = mp.Process(target=row_read_func, args=(3, 1))
    # read_proc_2 = mp.Process(target=row_read_func, args=(4, 2))

    l_proc = [
              write_proc_1,
              write_proc_2,
              read_proc_1,
              # read_proc_2
              ]
    for proc in l_proc:
        proc.start()

    while len(l_proc) > 0:
        for proc in l_proc:
            if proc.is_alive():
                proc.join(0.1)
            else:
                l_proc.remove(proc)
    logging.debug('[row_lock_test] Done.')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # create_table()
    # insert_data_rec()
    # fetch_data_rec()
    row_lock_test()
