import logging
import socket


class SocketDemoServer:

    SERV_PORT = 1234
    BUFF_SIZE = 65565
    ACK_MSG = 'ACK'

    # To start the network communication, we need to create a socket instance first. And all network communications will be done via this socket instance. This instance contains information about the sender's network address, connection type and others.

    # Create a Socket
    # AF_INET: IPv4
    # SOCK_DGRAM: UDP
    g_serv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Store received messages
    g_msg_list = []

    @classmethod
    def msg_handler(cls, msg, addr):
        """
        We handle received messages in this function.
        :param msg: The message itself.
        :param addr: The address of the sender.
        """
        logging.info('[SERVER:msg_handler] Starts to process msg.')
        # A message is of the type 'bytes' instead of string.
        l_fields = msg.decode('utf-8').split('|')
        # Parse the message and extract the fields.
        attr_id = int(l_fields[0].strip())
        attr_str = l_fields[1].strip()
        attr_val = float(l_fields[2].strip())
        # Add the message into the list.
        cls.g_msg_list.append((attr_id, attr_str, attr_val))
        logging.info('[SERVER:msg_handler] Received ID:%s, STR:%s, VAL:%s' % (attr_id, attr_str, attr_val))
        logging.info('[SERVER:msg_handler] g_msg_list = %s' % cls.g_msg_list)
        # Send an acknowledgement to the sender to indicate that the server has received the message.
        logging.info('[SERVER:msg_handler] Send an ACK to client')
        cls.g_serv_sock.sendto(str.encode(cls.ACK_MSG + '|' + l_fields[0].strip()), addr)
        logging.info('[SERVER:msg_handler] Done sending the ACK to client.')

    @classmethod
    def server_start(cls):
        """
        This function is the main loop of the server. It keeps listening on the specified port and receiving messages from client.
        """
        logging.info('[SERVER:server_start] Server starts.')
        # Bind the Socket with all available network interfaces and the port number
        cls.g_serv_sock.bind(("", cls.SERV_PORT))
        logging.info('[SERVER:server_start] Bind is done.')
        # Loop listening incoming messages
        while True:
            logging.info('[SERVER:server_start] Inside while, listening...')
            # Receive messages from client
            msg, addr = cls.g_serv_sock.recvfrom(cls.BUFF_SIZE)
            logging.info('[SERVER:server_start] Received a msg: msg=%s, ip=%s, port=%s' % (msg, addr[0], addr[1]))
            # Process the received message
            cls.msg_handler(msg, addr)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.info('[SERVER:main] main starts.')
    SocketDemoServer.server_start()
    logging.info('[SERVER:main] All done.')