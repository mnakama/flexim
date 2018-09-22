import json
import msgpack
import socket
import sys
import time
from tkinter import *
from enum import Enum
from tkinter.scrolledtext import ScrolledText
import _tkinter

from util import timestamp, Socket
from hyperlink import Hyperlink

class Mode(Enum):
    text = 1
    command = 2
    json = 3
    msgpack = 4


class Peer():
    def __init__(self):
        self._name = None
        self.nick = 'them'
        self.host = None
        self.port = None
        self.sock = None


    @property
    def name(self):
        if self._name:
            return self._name
        elif self.host and self.port:
            host = self.host
            port = self.port
        else:
            host, port = self.sock.getpeername()

        return '{}:{}'.format(host, port)


    @name.setter
    def name(self, name):
        self._name = name


    def recv(self, size):
        return self.sock.recv(size)


    def send(self, data):
        return self.sock.send(data)


    def sendall(self, data):
        return self.sock.sendall(data)


    def connect(self):
        self.sock = Socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.settimeout(5)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
        except Exception as e:
            self.sock = None
            raise


class ChatWindow(Tk):
    def __init__(self, sock=None, peer=None, address=None):
        failure = None

        self.peer = Peer()
        if peer:
            self.peer.host, self.peer.port = peer

        self.mode = Mode.msgpack
        self.sent_header = False
        self.address = address

        if sock:
            self.peer.sock = sock
            self.initiator = False

            header = self.peer.recv(5)
            if header[1:] != b'FLEX':
                Socket.abort(self.peer.sock, (b'Unrecognized protocol header\n'))
                print('Unrecognized protocol:', header)
                sys.exit(0)

            if header[0] == 0:
                self.mode = Mode.text
            elif header[0] == 0xa4:
                self.mode = Mode.msgpack
            elif header[0] == 0x22:
                self.mode = Mode.json
            else:
                Socket.abort(self.peer.sock, (b'Unrecognized protocol mode\n'))
                print('Unrecognized protocol mode:', header[0])
                sys.exit(0)


        elif peer:
            self.initiator = True
            try:
                self.connect()
            except Exception as e:
                failure = str(e)

        else:
            raise Exception("Missing required parameter")

        Tk.__init__(self)
        self.title(self.peer.name)

        #self.root = Tk()
        #self.main = Frame(self.root)
        self.main = Frame(self)
        self.main.pack(expand=True, fill=BOTH)

        self.chat_Text = ScrolledText(self.main)
        self.chat_Text.pack(expand=True, fill=BOTH)
        self.chat_Text['height'] = 10
        self.chat_Hyperlink = Hyperlink(self.chat_Text)

        self.send_Frame = Frame(self.main)
        self.send_Frame.pack(fill=X)

        self.send_Text = Text(self.send_Frame)
        self.send_Text.pack(side=LEFT, expand=True, fill=X)
        self.send_Text['height'] = 2
        self.send_Text.bind('<Shift-Return>', self.send_Newline)
        self.send_Text.bind('<Control-Return>', self.send_Newline)
        self.send_Text.bind('<Return>', self.send_Action)
        self.send_Button = Button(self.send_Frame, text='Send', command=self.send_Action)
        self.send_Button.pack(side=LEFT)

        self.status_Label = Label(self.main, text='Peer: {}'.format(self.peer.name))
        self.status_Label.pack()

        self.send_Text.focus()

        if failure:
            self.disable(failure)
        else:
            try: #this only works in linux for some reason
                self.checker = None
                self.tk.createfilehandler(self.peer.sock, _tkinter.READABLE, self.eventChecker)

            except: #rescue windows
                traceback.print_exc()
                print ('Windows mode!')
                sock.setblocking(False)
                self.checker = self.main.after(100, self.eventChecker)


    @property
    def mode(self):
        return self.receive_mode


    @mode.setter
    def mode(self, mode):
        self.receive_mode = mode
        self.send_mode = mode


    @property
    def receive_mode(self):
        return self._receive_mode


    @receive_mode.setter
    def receive_mode(self, mode):
        if mode == Mode.msgpack:
            self.unpacker = msgpack.Unpacker(raw=False)
        else:
            self.unpacker = None

        self._receive_mode = mode


    def send_Newline(self, *args):
        # Let the default handler make a newline. This exists
        # just to prevent the send_Action handler from activating
        pass


    def destroy(self):
        Tk.destroy(self)


    def append_text(self, text):
        scroll = self.chat_Text.yview()[1]

        # find hyperlinks and link them
        i = text.find('http://')
        if i < 0: i = text.find('https://')

        if i >= 0:
            self.append_text(text[:i])
            text = text[i:]

            # find the end of the link text
            i = text.find(' ')
            j = text.find('\n')

            if i < 0:
                i = j
            elif i >= 0 and j >= 0:
                i = min(i, j)

            if i >= 0:
                self.chat_Hyperlink.add(END, text[:i])
                self.append_text(text[i:])
            else:
                self.chat_Hyperlink.add(END, text)

        else:
            self.chat_Text.insert(END, text)


        if scroll >= 0.99:
            self.chat_Text.yview_moveto(1.0)


    def send_Action(self, *args):
        if not self.peer.sock: return 'break'

        text = self.send_Text.get('1.0', END)
        text = text.strip()

        self.send_Text.delete('1.0', END)

        if not text: return 'break'


        # /me is a "social command", so it's exempt from command processing
        if text[0] == '/' and not text.startswith('/me '):
            if text == '/bye':
                self.send_command('BYE ')
            elif text == '/text':
                self.send_command('TEXT')
                self.send_mode = Mode.text
            elif text == '/json':
                self.send_command('JSON')
                self.send_mode = Mode.json
                self.send_header_once()
            elif text == '/msgpack':
                self.send_command('MPCK')
                self.send_mode = Mode.msgpack
                self.send_header_once()
            else:
                self.append_text('Unrecognized command: {}\n'.format(text))
        else:
            if self.send_mode == Mode.text:
                message = (text + '\n').encode(encoding='utf8')
            elif self.send_mode in (Mode.json, Mode.msgpack):
                p = {
                    'category': 'chat',
                    'subject': '',
                    'flags': [],
                    'date': int(time.time()),
                    'message': text,
                }

                if self.send_mode == Mode.json:
                    message = json.dumps(p).encode(encoding='utf8')
                elif self.send_mode == Mode.msgpack:
                    message = msgpack.dumps(p)

            self.append_text(timestamp() + ' me: ' + text + '\n')
            self.peer.sendall(message)

        # Prevent default handler from adding a newline to the input textbox
        return 'break'


    def send_command(self, cmd):
        if self.send_mode == Mode.text:
            self.peer.sendall(b'\0' + cmd.encode(encoding='ascii'))
        elif self.send_mode in (Mode.json, Mode.msgpack):
            data = {
                'category': 'command',
                'flags': [],
                'date': int(time.time()),
                'message': str(cmd),
            }

            if self.send_mode == Mode.json:
                message = json.dumps(data).encode(encoding='ascii')
            elif self.send_mode == Mode.msgpack:
                message = msgpack.dumps(data)

            self.peer.sendall(message)


    def send_header_once(self):
        if not self.sent_header and self.initiator:
            self.send_header()
            self.sent_header = True


    def send_header(self):
        data = {
            'to': self.peer.name,
            'from': str(self.address),
            'options': [],
        }

        if self.send_mode == Mode.json:
            p = json.dumps(data).encode(encoding='utf8')
            self.peer.sendall(p)

        elif self.send_mode == Mode.msgpack:
            p = msgpack.dumps(data)
            self.peer.sendall(p)


    def update_peer_address(self, addr):
        self.peer.name = addr
        self.status_Label['text'] = 'Peer: ' + addr


    def process_header(self, header):
        self.update_peer_address(header['from'])


    def process_message(self, message):
        print('loads:', message)

        if 'to' in message:
            self.process_header(message)

        elif message['category'] == 'command':
            print('command:', message['message'])
            cmd = message['message']
            self.process_command(cmd)

        else:
            self.append_text('{} {}: {}\n'.format(timestamp(), self.peer.nick, message['message']))


    def process_command(self, cmd, more=None):
        if cmd == 'JSON':
            self.unpacker = None
            self.receive_mode = Mode.json

            if more:
                self.process_packet(more)

        elif cmd == 'MPCK':
            self.receive_mode = Mode.msgpack
            self.unpacker = msgpack.Unpacker(raw=False)

            if more:
                self.process_packet(more)

        elif cmd == 'TEXT':
            self.unpacker = None
            self.receive_mode = Mode.text

        elif cmd == 'BYE ':
            self.disable('Disconnecting: Bye\n')
            self.disconnect()

    def process_packet(self, packet):
        if self.receive_mode == Mode.text:
            p = packet.split(b'\0', 1)
            if p[0]:
                text = str(p[0], encoding='utf8')
                self.append_text(timestamp() + ' them: ' + text)

            if len(p) > 1:
                cmd = p[1][:4]
                more = p[1][4:]

                self.process_command(str(cmd, encoding='ascii'), more)

        elif self.receive_mode == Mode.json:
            message = json.loads(str(packet, encoding='utf8'))

            self.process_message(message)

        elif self.receive_mode == Mode.msgpack:
            self.unpacker.feed(packet)

            for o in self.unpacker:
                self.process_message(o)


    def eventChecker(self, *args): #could be (self, socket_fd, mask)
        try:
            try:
                packet = self.peer.recv(4096)
            except Exception as e:
                self.disable(str(e) + '\n')
                self.disconnect()
                return

            print('packet:', packet, len(packet))
            if len(packet) == 0:
                self.disable('Disconnected\n')
                self.disconnect()
            else:
                self.process_packet(packet)
        finally:
            if self.checker != None:
                self.checker = self.main.after(100, self.eventChecker)


    def connect(self):
        self.peer.connect()
        if self.send_mode == Mode.msgpack:
            header = b'\xa4FLEX'
            self.peer.send(header)
            self.send_header_once()
        elif self.send_mode == Mode.json:
            header = b'"FLEX'
            self.peer.send(header)
            self.send_header_once()
        else:
            header = b'\0FLEX'
            self.peer.send(header)


    def disconnect(self):
        self.tk.deletefilehandler(self.peer.sock)
        self.peer.sock.close()
        self.peer.sock = None


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
    def new_chat(peer, address):
        print("New peer:", peer)
        wnd = ChatWindow(peer=peer, address=address)
        wnd.main.mainloop()
