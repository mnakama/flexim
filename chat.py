import socket
import sys
from tkinter import *
from tkinter.scrolledtext import ScrolledText
import _tkinter

from util import timestamp, Socket

flexim_header = b'\0FLEX'

class ChatWindow(Tk):
    def __init__(self, sock=None, peer=None):
        failure = None

        if sock:
            self.sock = sock
            peer = self.sock.getpeername()

            header = self.sock.recv(5)
            if header != flexim_header:
                Socket.abort(self.sock, (b'Unrecognized protocol header\n'))
                sys.exit(0)

        elif peer:
            self.sock = Socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.settimeout(5)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.connect(peer)
                self.sock.settimeout(None)
                self.sock.send(flexim_header)
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


    def append_text(self, text):
        scroll = self.chat_Text.yview()[1]

        self.chat_Text.insert(END, text)
        if scroll >= 0.99:
            self.chat_Text.yview_moveto(1.0)


    def send_Action(self, *args):
        if not self.sock: return

        text = self.send_Text.get()
        text = text.strip()

        self.send_Text.delete(0, END)

        if not text: return
        message = text + '\n'

        self.append_text(timestamp() + ' me: ' + message)
        self.sock.sendall(message.encode())


    def eventChecker(self, *args): #could be (self, socket_fd, mask)
        try:
            try:
                message = self.sock.recv(4096)
            except Exception as e:
                self.disable(str(e) + '\n')

                self.tk.deletefilehandler(self.sock)
                self.sock.close()
                self.sock = None
                return

            print('message:', message, len(message))
            if len(message) == 0:
                self.disable('Disconnected\n')

                self.tk.deletefilehandler(self.sock)
                self.sock.close()
                self.sock = None
            else:
                message = str(message, encoding='utf8')
                self.append_text(timestamp() + ' them: ' + message)
        finally:
            if self.checker != None:
                self.checker = self.main.after(100, self.eventChecker)


    def disable(self, message):
        self.append_text(timestamp() + ' ' + message)
        self.chat_Text.yview_moveto(1.0)
        self.send_Text.config(state='disabled')
        self.send_Button.config(state='disabled')


    @staticmethod
    def give_socket(sock):
        print("I got a socket:", sock)
        wnd = ChatWindow(sock=sock)
        wnd.main.mainloop()


    @staticmethod
    def new_chat(peer):
        print("New peer:", peer)
        wnd = ChatWindow(peer=peer)
        wnd.main.mainloop()
