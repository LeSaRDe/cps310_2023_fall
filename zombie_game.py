import logging
import pickle
from logging import handlers
import os
import sys
import pathlib
import time
from datetime import datetime
import json
import multiprocessing as mp
import socket

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import psycopg as pg


##################################################
#   Global Definitions
##################################################
#----- Program Config -----#
# Global unique run ID
# TODO
#   Uncomment the following line to actual runs.
# RUN_ID = datetime.now().strftime('%Y%m%d%H%M%S')
RUN_ID = 'test_only'

# RUN_ID file
RUN_ID_FILE = pathlib.Path('.', 'RUN_ID')

# Output folder:
OUT_FOLDER = pathlib.Path(pathlib.Path.cwd(), 'out', RUN_ID)
if not OUT_FOLDER.exists():
    OUT_FOLDER.mkdir(parents=True)
else:
    raise Exception('Output Folder %s already existed.' % OUT_FOLDER)

# Log level
LOG_LEVEL = logging.DEBUG
# LOG_LEVEL = logging.INFO

# Log file
LOG_FILE = pathlib.Path(OUT_FOLDER, '%s.log' % RUN_ID)
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

# Config summary file
CONFIG_SUM_FILE = pathlib.Path(OUT_FOLDER, 'config_%s.json' % RUN_ID)

# Agent types
HUMAN = 1
DOCTOR = 2
ZOMBIE = 4

# Agent states
ALIVE = 1
INFECTED = 2
DEAD = 4


##################################################
#   Simulation
##################################################
class ZombieGameSim:
    # (class variable) The current moment
    m_cur_moment = None
    # Instance of GameLog
    m_logger = None

    def __init__(self):
        self.m_logger = GameLog()

    def get_logger(self, logger_name=None):
        if self.m_logger is None:
            raise Exception('[ZombieGameSim:get_logger] GameLog has not been initialized.')
        return self.m_logger.get_logger(log_level=LOG_LEVEL, logger_name=logger_name)

    @classmethod
    def GET_CUR_MOMENT(cls):
        return ZombieGameSim.m_cur_moment


##################################################
#   Data Backend
##################################################
class DataBroker:
    #----- Request Format -----#
    # [CMD]#[COND]#[ATTR1|ATTR2|...]#[VAL1|VAL2|...]
    # - CMD: (Mandatory)
    #   - 'T': Terminate the server.
    #   - 'R': Register notification listener.
    #   - 'S': select
    #   - 'U': update
    #   - 'I': insert
    # - COND: (Mandatory)
    #   - Condition string.
    #   - Can be the empty string, i.e., ''.
    # - ATTRi: (Mandatory)
    #   - ith attribute name.
    #   - Separated by '|'.
    #   - Can be '*'.
    # - VALi: (Mandatory for 'U' and 'I')
    #   - Value associated with ith attribute.
    #   - 'S' cmd does not have the value field.

    #----- Response Format -----#
    # - Respond to 'S'
    #   - One or multiple messages will be sent back to client.
    #   - For each response message: [AID]#[ATTR1|ATTR2|...]#[VAL1|VAL2|...]

    # Reference to GameConfig.
    m_ref_config = None
    # Logger
    m_logger = None
    # The request receiver process.
    m_receiver = None
    # The request queue.
    m_request_q = None
    # The server process.
    m_server = None

    def __init__(self, ref_config):
        self.m_logger = GameLog.get_logger(log_level=LOG_LEVEL, logger_name='DataBroker')
        if ref_config is None or not isinstance(ref_config, GameConfig):
            raise Exception('[DataBroker:__init__] GameConfig has not been initialized.')
        self.m_ref_config = ref_config
        self.__init_db()
        self.m_request_q = mp.Queue(-1)
        self.m_receiver = mp.Process(target=self.__receiver_func, args=(), name='BR_RECV')
        self.m_server = mp.Process(target=self.__server_func, args=(), name='BR_SERV')
        self.m_server.start()

    def __init_db(self):
        """
        Create `agent_status` table in DB, if it doesn't exist.
        :return: None.
        """
        with pg.connect(host=self.m_ref_config.DB_HOST,
                        dbname=self.m_ref_config.DB_NAME,
                        user=self.m_ref_config.DB_USER,
                        password=self.m_ref_config.DB_PASSWORD) as db_con:
            with db_con.cursor() as db_cur:
                sql_str = """create table if not exists agent_status (
                                    tick serial,
                                    aid serial,
                                    role serial,
                                    state smallserial,
                                    energy integer,
                                    x_pos real,
                                    y_pos real,
                                    primary key (tick, aid)
                                    )
                           """
                try:
                    db_cur.execute(sql_str)
                except Exception as e:
                    self.m_logger.error('[DataBroker:__init_db] Failed to create table `agent_status`: %s' % e)
                    sys.exit(-1)
        self.m_logger.debug('DataInit [DataBroker:__init_db] Done.')

    @staticmethod
    def send_request(host, port, cmd_str, cond_str, attr_str, val_str=None):
        """
        Invoked by working processes to send a request to DataBroker.
        :param host: (str)
        :param port: (int)
        :param cmd_str: (str)
        :param cond_str: (str)
        :param attr_str: (str)
        :param val_str: (str)
        :return: None
        """
        logger = GameLog.get_logger(log_level=LOG_LEVEL, logger_name=mp.current_process().name)
        l_req_field = []
        if cmd_str is not None:
            l_req_field.append(cmd_str)
            if cond_str is not None:
                l_req_field.append(cond_str)
                if attr_str is not None:
                    l_req_field.append(attr_str)
                else:
                    logger.error('[DataBroker:send_request] `attr_str` is needed.')
                    return
            else:
                logger.error('[DataBroker:send_request] `cond_str` is needed.')
                return
        else:
            logger.error('[DataBroker:send_request] `cmd_str` is needed.')
            return
        if val_str is not None:
            l_req_field.append(val_str)
        request_str = '#'.join(l_req_field)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.bind((host, port))
        client_sock.sendto(str.encode(request_str), (GameConfig.BR_HOST, GameConfig.BR_PORT))

    @staticmethod
    def get_notifier(host, port):
        """
        Start a process listening to notifications sent from DataBroker.
        :return: (multiprocessing.Queue)
        """
        notification_q = mp.Queue(-1)
        listen_proc = mp.Process(target=DataBroker.__notification_listen_func,
                                 args=(host, port, notification_q),
                                 name='%s_N' % mp.current_process().name)
        listen_proc.start()

    @staticmethod
    def __notification_listen_func(host, port, notification_q):
        """
        Notifications:
            - 'P': Pause incoming requests.
            - 'C': Continue sending requests.
            - 'T': Terminate notifier.
        :param host: (str)
        :param port: (int)
        :param notification_q: (multiprocessing.Queue)
        :return: None
        """
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.bind((host, port))
        logger = GameLog.get_logger(log_level=LOG_LEVEL, logger_name=mp.current_process().name)
        logger.debug('[DataBroker:__notification_listen_func] Notifier started.')
        while True:
            msg, addr = client_sock.recvfrom(1024)
            if addr[0] != GameConfig.BR_HOST or addr[1] != GameConfig.BR_PORT:
                continue
            msg = msg.decode('utf-8')
            if msg == 'P':
                logger = GameLog.get_logger(log_level=LOG_LEVEL, logger_name=mp.current_process().name)
                logger.debug('[DataBroker:__notification_listen_func] Pause sending requests.')
                notification_q.put_nowait('P')
            elif msg == 'C':
                logger = GameLog.get_logger(log_level=LOG_LEVEL, logger_name=mp.current_process().name)
                logger.debug('[DataBroker:__notification_listen_func] Continue sending requests.')
                notification_q.put_nowait('C')
            elif msg == 'T':
                break
        logger = GameLog.get_logger(log_level=LOG_LEVEL, logger_name=mp.current_process().name)
        logger.debug('[DataBroker:__notification_listen_func] Terminate notifier.')

    def __receiver_func(self):
        """
        Receive data operation requests from working processes, and enqueue requests. When the queue length reaches
        10% of the expected length, the receiver pauses incoming streams, and will continue when the length is lower
        than 50%. The pause msg sent by the receiver is a single msg with 'P'.
        :return: None
        """
        l_listener_addr = []
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind((GameConfig.BR_HOST, GameConfig.BR_PORT))
        while True:
            msg, addr = recv_sock.recvfrom(GameConfig.BR_BUFF_SIZE)
            msg = msg.decode('utf-8')
            if msg == 'T':
                # Terminate the server process.
                self.m_request_q.put_nowait(None)
                # Terminate all notification listener processes.
                for listener_addr in l_listener_addr:
                    recv_sock.sendto('T', listener_addr)
            elif msg == 'R':
                # Register notification listener.
                l_listener_addr.append(addr)
            else:
                # If the request queue is likely to be overwhelmed, send msg 'P' to request senders to pause incoming
                # requests.
                if self.m_request_q.qsize() >= GameConfig.BR_Q_EXP_LEN * 0.1:
                    recv_sock.sendto('P', addr)
                self.m_request_q.put([msg, addr])

    def __server_func(self):
        """
        The server process function processing incoming DB requests.
        NOTE:
            `psycopg` will automatically commit before every `select`. Thus, we refrain manual commit.
        :return: None.
        TODO
            Need a request queue.
        """
        self.m_logger.info('[DataBroker:__server_func] DataBroker started.')
        with pg.connect(host=self.m_ref_config.DB_HOST,
                        dbname=self.m_ref_config.DB_NAME,
                        user=self.m_ref_config.DB_USER,
                        password=self.m_ref_config.DB_PASSWORD) as db_con:
            with db_con.cursor() as db_cur:
                while True:
                    request, addr = self.m_request_q.get()
                    if request is None:
                        db_con.commit()
                        break
                    sql_str, data_fb = self.__parse_request(request)
                    db_cur.execute(sql_str)
                    # Data feedback is needed.
                    # if data_fb:
        self.m_request_q.close()
        self.m_logger.info('[DataBroker:__server_func] DataBroker stopped.')

    def __parse_request(self, raw_msg):
        """
        Parse a raw message received from a simulation working process to a SQL query string.
        :param raw_msg: (bytes) The raw message.
        :return:  tuple((str or None), bool) The first component is the translated SQL string. The second component
            indicates if data feedback is needed.
        """
        if raw_msg is None or len(raw_msg) <=0 or not isinstance(raw_msg, str):
            self.m_logger.error('[DataBroker:__parse_request] Invalid message: %s' % raw_msg)
            return None, False

        l_msg_fields = raw_msg.decode('utf-8').split('#')
        # Termination cmd
        if l_msg_fields[0] == 'T':
            return 'T', False

        if len(l_msg_fields) < 3:
            self.m_logger.error('[DataBroker:__parse_request] Need at least 3 fields: %s' % raw_msg)
            return None, False

        # Parse conditions
        cond = l_msg_fields[1]
        if cond == '':
            sql_cond = None
        else:
            sql_cond = cond

        # Parse attributes
        l_attr = l_msg_fields[2].split('|')
        if len(l_attr) < 1:
            self.m_logger.error('[DataBroker:__parse_request] Invalid ATTRIBUTE field: %s' % raw_msg)
            return None, False

        # Parse command
        data_feedback = False
        cmd = l_msg_fields[0]
        if cmd == 'S':
            data_feedback = True
            sql_attr = ','.join(l_attr)
            if sql_cond is not None:
                sql_str = """SELECT %s FROM agent_status WHERE %s""" % (sql_attr, sql_cond)
            else:
                sql_str = """SELECT %s FROM agent_status""" % (sql_attr)
        else:
            if len(l_msg_fields) < 4:
                self.m_logger.error('[DataBroker:__parse_request] Need at least 4 fields: %s' % raw_msg)
                return None, False
            l_val = l_msg_fields[3].split('|')
            if len(l_val) < 1:
                self.m_logger.error('[DataBroker:__parse_request] Invalid VALUE field: %s' % raw_msg)
                return None, False
            if len(l_attr) != len(l_val):
                self.m_logger.error('[DataBroker:__parse_request] VALUE field does not match ATTRIBUTE field: %s'
                                    % raw_msg)
                return None, False
            if cmd == 'U':
                sql_set_str = ','.join(['%s=%s'] * len(l_attr)) % tuple(sum(zip(l_attr, l_val), ()))
                if sql_cond is not None:
                    sql_str = """UPDATE agent_status SET %s WHERE %s""" % (sql_set_str, sql_cond)
                else:
                    sql_str = """UPDATE agent_status SET %s""" % (sql_set_str)
            elif cmd == 'I':
                if len(l_attr) != 7:
                    self.m_logger.error('[DataBroker:__parse_request] Need exactly 7 attributes for INSERT: %s'
                                        % raw_msg)
                    return None, False
                sql_attr = ','.join(l_attr)
                sql_val = ','.join(l_val)
                sql_str = """INSERT INTO agent_status(%s) VALUES (%s)""" % (sql_attr, sql_val)
            else:
                self.m_logger.error('[DataBroker:__parse_request] Unsupported data cmd: %s' % cmd)
                return None, False
        return sql_str, data_feedback

    def stop_br(self):
        """
        Send the termination cmd to the server process.
        :return: None.
        """
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.sendto(str.encode('T'), (self.m_ref_config.BR_HOST, self.m_ref_config.BR_PORT))
        self.m_server.join()
        self.m_logger.info('[DataBroker:stop_br] DataBroker stopped.')


def utest_DataBroker():
    ins_gl = GameLog()
    ins_gc = GameConfig(ins_gl)
    ins_br = DataBroker(ins_gl, ins_gc)

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)






##################################################
#   Utility Classes
##################################################
class GameConfig:
    # ----- Logger Config -----#
    LG_HOST = 'localhost'
    LG_PORT = 1234
    LG_BUFF_SIZE = 4096

    # ----- Database Config -----#
    DB_HOST = 'localhost'
    DB_NAME = 'zombie_game_db'
    DB_USER = 'fmeng'
    DB_PASSWORD = 'michal'

    # ----- DataBroker Config -----#
    BR_HOST = 'localhost'
    BR_PORT = 2345
    BR_BUFF_SIZE = 10240
    BR_Q_EXP_LEN = 1000

    # ----- Simulation Config -----#
    # Max iterations
    # TODO
    #   Change it.
    MAX_ITER = 2000

    # Total number of agents
    # TODO
    #   Change it.
    NUM_AGENTS = 500

    # Number of neighbors for each agent
    # TODO
    #   Change it.
    #   NOTE: Only applicable to cases of a constant number of neighbors.
    NUM_NEIG = 10

    # Probabilities of agents
    # TODO
    #   Change them.
    H_PROB = 0.25
    D_PROB = 0.25
    Z_PROB = 0.5

    # Initial energies
    # TODO
    #   Change them.
    H_ENERGY = 500
    D_ENERGY = 500
    Z_ENERGY = 100

    # TODO
    #   Change the following parameters.
    # ----- Zombie Config -----#
    BITE_PROB = 0.3
    # The energy increase from a bite.
    BITE_GAIN = 5
    # The energy change of being a Zombie
    Z_DECAY = -1

    # ----- Human Config -----#
    # The energy change caused by a bite.
    BITE_HURT = -5
    # The energy change due to the infection.
    H_DECAY = -1
    # The energy increase due to the healing.
    LIFE_GAIN = 1

    # ----- Doctor Config -----#
    BITE_EFF = 5

    # Config data
    m_d_config = None
    # Logger
    m_logger = None

    @classmethod
    def config_init(cls, config_file_path=None):
        if config_file_path is not None and not os.path.exists(config_file_path):
            with open(config_file_path, 'r') as in_fd:
                try:
                    d_config = json.load(in_fd)
                    cls.__set_config(d_config)
                except Exception as e:
                    print('[GameConfig:__init__] Failed to open config file: %s' % e)
                    sys.exit(-1)

    @classmethod
    def __set_config(cls, d_config):
        if d_config is None:
            print('[GameConfig:__set_config] Use default config.')
        else:
            cls.MAX_ITER = d_config['MAX_ITER'] if 'MAX_ITER' in d_config else cls.MAX_ITER
            cls.NUM_AGENTS = d_config['NUM_AGENTS'] if 'NUM_AGENTS' in d_config else cls.NUM_AGENTS
            cls.NUM_NEIG = d_config['NUM_NEIG'] if 'NUM_NEIG' in d_config else cls.NUM_NEIG
            cls.H_PROB = d_config['H_PROB'] if 'H_PROB' in d_config else cls.H_PROB
            cls.D_PROB = d_config['D_PROB'] if 'D_PROB' in d_config else cls.D_PROB
            cls.Z_PROB = d_config['Z_PROB'] if 'Z_PROB' in d_config else cls.Z_PROB
            cls.H_ENERGY = d_config['H_ENERGY'] if 'H_ENERGY' in d_config else cls.H_ENERGY
            cls.D_ENERGY = d_config['D_ENERGY'] if 'D_ENERGY' in d_config else cls.D_ENERGY
            cls.Z_ENERGY = d_config['Z_ENERGY'] if 'Z_ENERGY' in d_config else cls.Z_ENERGY
            cls.BITE_PROB = d_config['BITE_PROB'] if 'BITE_PROB' in d_config else cls.BITE_PROB
            cls.BITE_GAIN = d_config['BITE_GAIN'] if 'BITE_GAIN' in d_config else cls.BITE_GAIN
            cls.Z_DECAY = d_config['Z_DECAY'] if 'Z_DECAY' in d_config else cls.Z_DECAY
            cls.BITE_HURT = d_config['BITE_HURT'] if 'BITE_HURT' in d_config else cls.BITE_HURT
            cls.H_DECAY = d_config['H_DECAY'] if 'H_DECAY' in d_config else cls.H_DECAY
            cls.LIFE_GAIN = d_config['LIFE_GAIN'] if 'LIFE_GAIN' in d_config else cls.LIFE_GAIN
            cls.BITE_EFF = d_config['BITE_EFF'] if 'MAX_ITER' in d_config else cls.BITE_EFF
            cls.m_logger.debug('[GameConfig:__set_config] Successfully loaded in custom config.')

    @classmethod
    def config_summary(cls):
        """
        Summarize all configurations in a JSON file.
        :return: None.
        """
        d_config = {
            'MAX_ITER': cls.MAX_ITER,
            'NUM_AGENTS': cls.NUM_AGENTS,
            'NUM_NEIG': cls.NUM_NEIG,
            'H_PROB': cls.H_PROB,
            'D_PROB': cls.D_PROB,
            'Z_PROB': cls.Z_PROB,
            'H_ENERGY': cls.H_ENERGY,
            'D_ENERGY': cls.D_ENERGY,
            'Z_ENERGY': cls.Z_ENERGY,
            'BITE_PROB': cls.BITE_PROB,
            'BITE_GAIN': cls.BITE_GAIN,
            'Z_DECAY': cls.Z_DECAY,
            'BITE_HURT': cls.BITE_HURT,
            'H_DECAY': cls.H_DECAY,
            'LIFE_GAIN': cls.LIFE_GAIN,
            'BITE_EFF': cls.BITE_EFF
        }
        with open(CONFIG_SUM_FILE, 'w') as out_fd:
            json.dump(d_config, out_fd, indent=4)
        print('[GameConfig:config_summary] Done writing config summary file: %s' % CONFIG_SUM_FILE)


class GameLog:
    # Log listener process.
    m_log_listen_proc = None

    @classmethod
    def start_log(cls):
        cls.m_log_listen_proc = mp.Process(target=GameLog.__log_listener, args=())
        cls.m_log_listen_proc.start()

    @staticmethod
    def __init_logger():
        # Create global logger.
        if LOG_FILE is not None:
            log_handler = logging.FileHandler(LOG_FILE)
        else:
            log_handler = logging.StreamHandler(sys.stdout)
        log_fmt = logging.Formatter('%(name)s %(levelname)s %(message)s')
        game_logger = logging.getLogger()
        log_handler.setFormatter(log_fmt)
        game_logger.addHandler(log_handler)
        game_logger.setLevel(LOG_LEVEL)

    @staticmethod
    def __log_listener():
        GameLog.__init_logger()
        serv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        serv_sock.bind((GameConfig.LG_HOST, GameConfig.LG_PORT))
        logger = logging.getLogger()
        logger.info('[GameLog:__log_listener] Started logging.')
        while True:
            try:
                msg, addr = serv_sock.recvfrom(GameConfig.LG_BUFF_SIZE)
                if msg[:1].decode('utf-8') == 'T':
                    break
                msg_rec = logging.makeLogRecord(pickle.loads(msg[4:]))
                logger = logging.getLogger(msg_rec.name)
                logger.handle(msg_rec)
            except Exception as e:
                print('[GameLog:__log_listener] Error: %s' % e)
        logger = logging.getLogger()
        logger.info('[GameLog:__log_listener] Stopped logging.')

    @classmethod
    def stop_log(cls):
        """
        `None` as a special log message is sent to the log listener, and then the listener quits after seeing it.
        :return: None.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(str.encode('T'), (GameConfig.LG_HOST, GameConfig.LG_PORT))
        cls.m_log_listen_proc.join()
        logger = logging.getLogger()
        logger.info('[GameLog:stop_log] GameLog stopped.')

    @classmethod
    def get_logger(cls, log_level=LOG_LEVEL, logger_name=None):
        """
        Returns a UDP-based logger.
        :return: (logging.Logger)
        """
        if cls.m_log_listen_proc is None:
            raise Exception('[GameLog:get_logger] The listener has not been initialized.')

        log_handler = handlers.DatagramHandler(GameConfig.LG_HOST, GameConfig.LG_PORT)
        logger = logging.getLogger()
        logger.addHandler(log_handler)
        logger.setLevel(log_level)
        if logger_name is not None:
            logger = logging.getLogger(logger_name)
        else:
            logger = logging.getLogger()
        return logger


def utest_GameLog():
    from random import random, choice

    GameLog.start_log()

    LEVELS = [logging.DEBUG, logging.INFO, logging.WARNING,
              logging.ERROR, logging.CRITICAL]

    MESSAGES = [
        'Random message #1',
        'Random message #2',
        'Random message #3',
    ]

    def worker_process(logger):
        name = mp.current_process().name
        print('Worker started: %s' % name)
        for i in range(10):
            time.sleep(random())
            level = choice(LEVELS)
            message = choice(MESSAGES)
            logger.log(level, message)
        print('Worker finished: %s' % name)

    workers = []
    for i in range(10):
        logger = GameLog.get_logger(log_level=LOG_LEVEL, logger_name='Logger_P#%s' % i)
        worker = mp.Process(target=worker_process,
                            args=(logger,))
        workers.append(worker)
        worker.start()
    for w in workers:
        w.join()

    GameLog.stop_log()


if __name__ == '__main__':
    utest_GameLog()