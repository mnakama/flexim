#!/usr/bin/python3
import multiprocessing as mp
import socket
import traceback

# Requires python 3 and tkinter
try:
    from tkinter import *
except ImportError:
    traceback.print_exc()
    print ('\nYou need to install tkinter (python 3)\nOn Redhat/Fedora, type: sudo yum install python3-tkinter')
    exit(1)

from tkinter.scrolledtext import ScrolledText
import _tkinter

from roster import RosterWindow
from chat import ChatWindow

default_port = 9000


def headless():
    try:
        while True:
            conn = sock.accept()[0]
            print('event!', conn)

            p = mp.Process(target=ChatWindow.give_socket, args=(conn,))
            p.start()
    finally:
        sock.close()


if __name__ == '__main__':
    # Tk will crash if we don't set this to "spawn", because it does not like multi-threading.
    mp.set_start_method('spawn')

    sock = None

    if '--nolisten' not in sys.argv:
        try:
            myport = int(sys.argv[1])
        except IndexError:
            myport = default_port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', myport))
        sock.listen()
    
    if '--headless' in sys.argv:
        headless()
    else:
        roster = RosterWindow(sock)
        try:
            roster.main.mainloop()
        finally:
            if sock:
                sock.close()
