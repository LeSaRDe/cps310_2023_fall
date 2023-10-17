import logging
import socket
import string
import time
from numpy import random

SERV_PORT = 1234
BUFF_SIZE = 65565

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    logging.info('[CLIENT:main] main starts.')
    # We need to create a socket instance for the client too.
    serv_addr = ('localhost', SERV_PORT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info('[CLIENT:main] After creating client Socket.')
    # We send out some messages.
    # for i in range(10):
    time_int_dur = 2 # in seconds
    mu = 5 # 'mean' parameter for the Poisson distribution
    job_id = 0
    i = 0
    while True:
        logging.debug('[CLIENT:main] Inside for loop: i=%s' % str(i))

        # Draw the number of jobs to be generated within a time interval.
        draw = random.poisson(lam=mu, size=1)
        n_jobs = draw[0]
        logging.debug('[CLIENT:main] Loop:%s, generate %s jobs.' % (i, n_jobs))
        for j in range(n_jobs):
            job_id = job_id + j
            attr_str = ''.join([chr(bt) for bt in random.choice(bytearray(string.ascii_lowercase, 'utf-8'), size=5)])
            attr_val = random.random(1)[0]
            sock.sendto(str.encode('|'.join([str(job_id), attr_str, str(attr_val)])), serv_addr)
            logging.debug('[CLIENT:main] Send out: ID:%s, STR:%s, VAL:%s' % (job_id, attr_str, attr_val))
            # We receive acknowledgements from the server.
            logging.debug('[CLIENT:main] Listening to incoming msg...')
            msg, addr = sock.recvfrom(BUFF_SIZE)
            logging.debug('[CLIENT:main] Received: MSG:%s' % msg)

        time.sleep(time_int_dur)
        logging.debug('[CLIENT:main] Done sleeping, and wake up.')
        i += 1

    logging.info('[CLIENT:main] All done.')
