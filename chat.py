import socket
from tkinter import *
from tkinter.scrolledtext import ScrolledText
import _tkinter

from util import timestamp

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
        self.chat_Text.yview_moveto(1.0)
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
                self.chat_Text.yview_moveto(1.0)
        finally:
            if self.checker != None:
                self.checker = self.main.after(100, self.eventChecker)


    def disable(self, message):
        self.chat_Text.insert(END, timestamp() + ' ' + message)
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
