#!/usr/bin/python3
import multiprocessing as mp
import socket
import traceback

# Requires python 3 and tkinter
from tkinter import *

from tkinter.scrolledtext import ScrolledText
import _tkinter

from chat import ChatWindow

default_port = 9000

class RosterWindow(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title('im2')
        self.main = Frame(self)
        self.main.pack(expand=True, fill=BOTH)

        self.host_Frame = Frame(self.main)
        self.host_Frame.pack(side=TOP)
        self.host_Label = Label(self.host_Frame, text='Message to "Host:Port":')
        self.host_Label.pack(side=LEFT)
        self.host_Entry = Entry(self.host_Frame)
        self.host_Entry.pack(side=LEFT)
        self.host_Entry.bind('<Return>', self.connect_Action)
        self.host_Entry.focus()
        self.host_Button = Button(self.host_Frame, text='Chat', command=self.connect_Action)
        self.host_Button.pack(side=LEFT)

        #debug
        self.host_Entry.insert(0, 'localhost:{}'.format(default_port))


    def destroy(self):
        Tk.destroy(self)


    def connect_Action(self, *args):
        peer = self.host_Entry.get()

        try:
            peer, port = peer.split(':', 1)
        except ValueError:
            #peer = socket.gethostbyname(peer)
            peer = (peer, default_port)
        else:
            #peer = socket.gethostbyname(peer)
            peer = (peer, int(port))

        print(peer)
        p = mp.Process(target=ChatWindow.new_chat, args=(peer,))
        p.start()


def main():
    # Tk will crash if we don't set this to "spawn", because it does not like multi-threading.
    mp.set_start_method('spawn')
    roster = RosterWindow()
    roster.main.mainloop()

if __name__ == '__main__':
    main()