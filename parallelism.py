import logging
import string
import sys
import time
import os
import math
import numpy as np
import multiprocessing as mp
from multiprocessing import shared_memory
import threading as th


def gen_rand_strings(cnt_str, min_str_len, max_str_len, out_path):
    """
    Generate random strings. The generated strings will be written in a text file. Each line holds a string.
    :param cnt_str: (str) The total number random string to be generated.
    :param min_str_len: (int) The min length of random strings.
    :param max_str_len: (int) The max length of random strings.
    :param out_path: (str) The path to the output text file.
    :return: None.
    """
    logging.debug('[gen_rand_strings] Start:\n cnt_str = %s\n out_path = %s' % (cnt_str, out_path))
    # The number of characters of each random string.
    l_cnt_char = np.random.randint(low=min_str_len, high=max_str_len, size=cnt_str)
    # All candidate characters.
    l_char = list(string.ascii_letters)
    # Generate random strings.
    l_rand_str = []
    for i in range(cnt_str):
        l_rand_str.append(''.join(np.random.choice(l_char, size=l_cnt_char[i])))
    # Write to a file.
    with open(out_path, 'w+') as out_fd:
        out_str = '\n'.join(l_rand_str)
        out_fd.write(out_str)
    logging.debug('[gen_rand_strings] All done.')


# def s_char_cnt(in_str, s_char):
#     """
#     Count the total number of a specified character in a given string.
#     :param in_str: (str) The given string.
#     :param s_char: (str) The specified character.
#     :return: (int) The count of the specified character.
#     """
#     # logging.debug('[s_char_cnt] Start:\n in_str = %s\n s_char = %s' % (in_str, s_char))
#
#     if in_str is None or len(in_str) <= 0:
#         logging.debug('[s_char_cnt] All done.\n Count = %s' % 0)
#         return 0
#
#     cnt_char = in_str.count(s_char)
#     # logging.debug('[s_char_cnt] All done.\n Count = %s' % cnt_char)
#     return cnt_char
#
#
# def single_task_s_char_cnt(in_path, s_char):
#     """
#     Count the total number of a specified characters in all input strings. The strings are read from an input file.
#     :param in_path: (str) The path to the input file containing strings.
#     :param s_char: (str) A single character to search in strings.
#     :return: (int) The total number of occurrences of the specified character in all input strings.
#     """
#     if not os.path.exists(in_path):
#         logging.error('[single_task_run] The input file path does not exist: %s' % in_path)
#         return None
#
#     if len(s_char) != 1:
#         logging.error('[single_task_run] `s_char` needs to be a single character.')
#         return None
#
#     with open(in_path, 'r') as in_fd:
#         l_rand_str = in_fd.readlines()
#
#     start_time = time.time()
#
#     cnt_char = 0
#     for rand_str in l_rand_str:
#         cnt_char += s_char_cnt(rand_str, s_char)
#
#     logging.debug('[single_task_run] All done.\n Total char count = %s\n Elapse = %s'
#                   % (cnt_char, time.time() - start_time))
#     return cnt_char


def multi_s_char_cnt(in_str, l_s_char):
    nd_char_cnt = np.zeros(len(l_s_char), dtype=int)
    for char in in_str:
        if char in l_s_char:
            idx = l_s_char.index(char)
            nd_char_cnt[idx] += 1
    return nd_char_cnt

def _batch_multi_s_char_cnt(l_str, l_s_char, out_array=None):
    """
    Count the number of occurrences of each specified characters in a given list of strings.
    :param l_str: (list of str) Guaranteed to be not None or empty. The given list of strings.
    :param l_s_char: (list of str) Guaranteed to be not None or empty. The specified characters.
    :param out_array: (1D ndarray) If `out_array` is not None, it will carry the output.
    :return: (1D ndarray) Each element corresponds to a character in `l_s_char`.
    """
    if out_array is not None and type(out_array) == np.ndarray:
        out_array.fill(0)
        nd_char_cnt = out_array
    else:
        nd_char_cnt = np.zeros(len(l_s_char))
    for rand_str in l_str:
        nd_each = multi_s_char_cnt(rand_str, l_s_char)
        nd_char_cnt += nd_each
    return nd_char_cnt

def single_task_multi_s_char_cnt(in_path, l_s_char):
    """
    Count the number of occurrences of each character in a given list of characters.
    :param in_path: (str) The path to the input file containing strings.
    :param l_s_char: (list of str) A list of characters.
    :return: (dict) Keys are characters. Values are counts.
    """
    logging.debug('[single_task_multi_s_char_cnt] Start.')
    if not os.path.exists(in_path):
        logging.error('[single_task_multi_s_char_cnt] The input file path does not exist: %s' % in_path)
        return None

    if l_s_char is None or len(l_s_char) <= 0:
        logging.error('[single_task_multi_s_char_cnt] `l_s_char` needs to be a nonempty list of characters.')
        return None

    with open(in_path, 'r') as in_fd:
        l_rand_str = in_fd.readlines()

    start_time = time.time()
    nd_char_cnt = _batch_multi_s_char_cnt(l_rand_str, l_s_char)
    logging.debug('[single_task_multi_s_char_cnt] All done.\n Char counts = %s\n Elapse = %s'
                  % (nd_char_cnt, time.time() - start_time))
    return nd_char_cnt


def multitask_multi_s_char_cnt(in_path, l_s_char, cnt_task=os.cpu_count(), type=0):
    """
    The multitask version of `single_task_multi_s_char_cnt`.
    :param cnt_task: (int) The number of tasks running in parallel.
    :param type: (int) 0 - multiprocessing; 1 - multithreading.
    """
    logging.debug('[multitask_multi_s_char_cnt] Start.')
    if not os.path.exists(in_path):
        logging.error('[multitask_multi_s_char_cnt] The input file path does not exist: %s' % in_path)
        return None

    if l_s_char is None or len(l_s_char) <= 0:
        logging.error('[multitask_multi_s_char_cnt] `l_s_char` needs to be a nonempty list of characters.')
        return None

    with open(in_path, 'r') as in_fd:
        l_rand_str = in_fd.readlines()

    if type == 0:
        task_carrier = mp.Process
    else:
        task_carrier = th.Thread

    start_time = time.time()
    # Split the input for multiple tasks.
    cnt_str_per_task = math.floor(len(l_rand_str) / cnt_task)
    l_task = [l_rand_str[i * cnt_str_per_task: (i + 1) * cnt_str_per_task] for i in range(cnt_task)]

    # Output array
    nd_out = np.zeros(len(l_s_char))

    # Spawn tasks
    nd_size_test = np.zeros(len(l_s_char), dtype=float)
    shm_size = nd_size_test.nbytes
    del nd_size_test
    l_task_ins = []
    l_out_array = []
    l_shm = []
    for idx, l_task_str in enumerate(l_task):
        shm = shared_memory.SharedMemory(name='shm_%s' % idx, create=True, size=shm_size)
        out_array = np.ndarray(len(l_s_char), dtype=int, buffer=shm.buf)
        task_ins = task_carrier(target=_batch_multi_s_char_cnt, args=(l_task_str, l_s_char, out_array))
        task_ins.start()
        l_task_ins.append(task_ins)
        l_out_array.append(out_array)
        l_shm.append(shm)

    while len(l_task_ins) > 0:
        for task_ins in l_task_ins:
            if task_ins.is_alive():
                task_ins.join(0.1)
            else:
                l_task_ins.remove(task_ins)

    for out_array in l_out_array:
        nd_out += out_array
        del out_array

    for shm in l_shm:
        shm.close()
        shm.unlink()

    logging.debug('[multitask_multi_s_char_cnt] All done.\n Char Counts = %s\n Elapse = %s'
                  % (nd_out, time.time() - start_time))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Get CMD
    if len(sys.argv) <= 1:
        logging.error('[__main__] Arguments are needed.')
        sys.exit(-1)

    cmd = sys.argv[1]
    if cmd == 'gen_rand_strings':
        if len(sys.argv) < 5:
            logging.error('[__main__] The format of this cmd is:\n'
                          '> python parallelism.py gen_rand_strings [COUNT OF STRINGS] [MIN STRING LENGTH] [MAX STRING LENGTH] [OUTPUT PATH]')
            sys.exit(-1)
        cnt_str = int(sys.argv[2])
        min_str_len = int(sys.argv[3])
        max_str_len = int(sys.argv[4])
        out_path = sys.argv[5]
        gen_rand_strings(cnt_str, min_str_len, max_str_len, out_path)

    elif cmd == 'single_task_multi_s_char_cnt':
        if len(sys.argv) < 2:
            logging.error('[__main__] The format of this cmd is:\n'
                          '> python parallelism.py single_task_multi_s_char_cnt [INPUT PATH] [LIST OF CHARACTERS]')
            sys.exit(-1)
        in_path = sys.argv[2]
        if len(sys.argv) > 3:
            l_s_char = list(sys.argv[3].strip())
        else:
            l_s_char = list(string.ascii_letters)
        single_task_multi_s_char_cnt(in_path, l_s_char)

    elif cmd == 'multitask_multi_s_char_cnt':
        if len(sys.argv) < 2:
            logging.error('[__main__] The format of this cmd is:\n'
                          '> python parallelism.py multitask_multi_s_char_cnt [INPUT PATH] [LIST OF CHARACTERS]')
            sys.exit(-1)
        in_path = sys.argv[2]
        if len(sys.argv) > 3:
            l_s_char = list(sys.argv[3].strip())
        else:
            l_s_char = list(string.ascii_letters)
        multitask_multi_s_char_cnt(in_path, l_s_char)
