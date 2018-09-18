#!/usr/bin/python3
import datetime
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

default_port = 9000

def timestamp():
	return '[' + datetime.datetime.now().strftime('%X') + ']'


class MainWindow(Tk):
    def __init__(self, sock):
        self.sock = sock

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

        try: #this only works in linux for some reason
            self.checker = None
            self.tk.createfilehandler(self.sock, _tkinter.READABLE, self.eventChecker)

        except: #rescue windows
            traceback.print_exc()
            print ('Windows mode!')
            self.sock.setblocking(False)
            self.checker = self.main.after(100, self.eventChecker)


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
        p = mp.Process(target=new_chat, args=(peer,))
        p.start()


    def eventChecker(self, *args): #could be (self, socket_fd, mask)
        try:
            print('event!', args)
            conn = self.sock.accept()[0]

            p = mp.Process(target=give_socket, args=(conn,))
            p.start()
        finally:
            if self.checker != None:
                self.checker = self.main.after(100, self.eventChecker)


class ChatWindow(Tk):
    def __init__(self, sock=None, peer=None):
        failure = None

        if sock:
            self.sock = sock
            peer = self.sock.getpeername()
        elif peer:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.settimeout(5)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.connect(peer)
                self.sock.settimeout(None)
            except Exception as e:
                failure = str(e)
                self.sock = None
        else:
            raise Exception("Missing required parameter")
        
        self.peer = peer

        Tk.__init__(self)
        self.title('{}:{}'.format(peer[0], peer[1]))

        #self.root = Tk()
        #self.main = Frame(self.root)
        self.main = Frame(self)
        self.main.pack(expand=True, fill=BOTH)

        self.chat_Text = ScrolledText(self.main)
        self.chat_Text.pack(expand=True, fill=BOTH)
        self.chat_Text['height'] = 10

        self.send_Frame = Frame(self.main)
        self.send_Frame.pack(fill=X)

        self.send_Text = Entry(self.send_Frame)
        self.send_Text.pack(side=LEFT, expand=True, fill=X)
        self.send_Text.bind('<Return>', self.send_Action)
        self.send_Button = Button(self.send_Frame, text='Send', command=self.send_Action)
        self.send_Button.pack(side=LEFT)

        self.status_Label = Label(self.main, text='Peer: {}:{}'.format(peer[0], peer[1]))
        self.status_Label.pack()

        self.send_Text.focus()

        if failure:
            self.disable(failure)
        else:
            try: #this only works in linux for some reason
                self.checker = None
                self.tk.createfilehandler(self.sock, _tkinter.READABLE, self.eventChecker)

            except: #rescue windows
                traceback.print_exc()
                print ('Windows mode!')
                sock.setblocking(False)
                self.checker = self.main.after(100, self.eventChecker)


    def destroy(self):
        Tk.destroy(self)


    def send_Action(self, *args):
        if not self.sock: return

        text = self.send_Text.get()
        message = text.strip() + '\n'

        self.send_Text.delete(0, END)

        if not message: return

        self.chat_Text.insert(END, timestamp() + ' me: ' + message)
        self.sock.sendall(message.encode())


    def eventChecker(self, *args): #could be (self, socket_fd, mask)
        try:
            message = self.sock.recv(4096)
            print('message:', message, len(message))
            if len(message) == 0:
                self.disable('Disconnected')

                self.tk.deletefilehandler(self.sock)
                self.sock.close()
                self.sock = None
            else:
                message = str(message, encoding='utf8')
                self.chat_Text.insert(END, timestamp() + ' them: ' + message)
        finally:
            if self.checker != None:
                self.checker = self.main.after(100, self.eventChecker)


    def disable(self, message):
        self.chat_Text.insert(END, timestamp() + ' ' + message)
        self.send_Text.config(state='disabled')
        self.send_Button.config(state='disabled')


def give_socket(sock):
    print("I got a socket:", sock)
    wnd = ChatWindow(sock=sock)
    wnd.main.mainloop()


def new_chat(peer):
    print("New peer:", peer)
    wnd = ChatWindow(peer=peer)
    wnd.main.mainloop()

if __name__ == '__main__':
    # Tk will crash if we don't set this to "spawn", because it does not like multi-threading.
    mp.set_start_method('spawn')

    try:
        myport = int(sys.argv[1])
    except IndexError:
        myport = default_port

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', myport))
    sock.listen()

    mainwindow = MainWindow(sock)
    try:
        mainwindow.main.mainloop()
    finally:
        sock.close()
