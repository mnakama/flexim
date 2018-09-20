#!/usr/bin/python3
import multiprocessing as mp
import socket
import sys
import traceback

from chat import ChatWindow
from util import Socket

default_port = 9000

def main():
    try:
        myport = int(sys.argv[1])
    except IndexError:
        myport = default_port
    sock = Socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', myport))
    sock.listen()

    with sock:
        while True:
            conn = sock.accept()[0]
            print('event!', conn)

            p = mp.Process(target=ChatWindow.give_socket, args=(conn,))
            p.start()

            # close our copy of the socket so the ChatWindow process can own it.
            conn.close()

if __name__ == '__main__':
    main()
