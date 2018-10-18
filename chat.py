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

_test_fragment = False

class Mode(Enum):
    text = 1
    command = 2
    json = 3
    msgpack = 4


class Datum(Enum):
    Auth = 0
    AuthResponse = 1
    Command = 2
    Message = 3
    Roster = 4
    User = 5


class Protocol():
    pass


class PText(Protocol):
    first_packet =b'\0FLEX'
    mode = Mode.text

    def __init__(self):
        self.rbuff = b''
        self.buffer = []


    def command(self, cmd, data=None):
        if not data:
            return b'\0' + cmd.encode(encoding='ascii')
        else:
            return b'\0' + cmd.encode(encoding='ascii') + data.encode(encoding='utf8')


    def header(self, header):
        return self.command('FROM' + header['from'] + '\n')


    def message(self, msg, **kwargs):
        return (msg + '\r').encode(encoding='utf8')


    def feed(self, packet):
        self.rbuff = self.rbuff + packet

        while len(self.rbuff):
            z = self.rbuff.find(b'\0')
            n = self.rbuff.find(b'\r')

            if z >= 0 and (n == -1 or z < n):
                text = str(self.rbuff[z+1:], encoding='utf8')

                datum = {
                    'cmd': text,
                    'payload': None,
                }

                self.buffer.append(datum)
                self.rbuff = b''

            elif n >= 0:
                text = str(self.rbuff[:n], encoding='utf8')

                datum = {
                    'to': '',
                    'from': '',
                    'flags': [],
                    'date': int(time.time()),
                    'msg': text,
                }

                self.buffer.append(datum)
                self.rbuff = self.rbuff[n+1:]

            else:
                break


    def read(self):
        while len(self.buffer):
            p = self.buffer.pop(0)
            yield p


class PDatum(Protocol):
    def command_data(self, cmd, data=None):
        data = {
            'cmd': str(cmd),
            'payload': data,
        }

        return data


    def message_data(self, msg, to='', From=''):
        p = {
            'to': to,
            'from': From,
            'flags': [],
            'date': int(time.time()),
            'msg': msg,
        }
        return p


class JSON(PDatum):
    first_packet = b'"FLEX'
    mode = Mode.json

    def __init__(self):
        self.buffer = []


    def command(self, cmd, data=None):
        data = self.command_data(cmd, data=data)

        message = json.dumps(data).encode(encoding='ascii')
        return message

    def header(self, header):
        json.dumps(header).encode(encoding='utf8')


    def message(self, msg, **kwargs):
        p = self.message_data(msg, **kwargs)
        return json.dumps(p).encode(encoding='utf8')


    def feed(self, packet):
        self.buffer.append(json.loads(str(packet, encoding='utf8')))


    def read(self):
        for p in self.buffer:
            self.buffer = self.buffer[1:]
            yield p


class Msgpack(PDatum):
    first_packet = b'\xa4FLEX'
    mode = Mode.msgpack

    def __init__(self):
        self.unpacker = msgpack.Unpacker(raw=False)
        self.datum_len = 0
        self.rbuff = b''
        self.buffer = []


    def command(self, cmd, data=None):
        data = self.command_data(cmd, data=data)

        p = msgpack.dumps(data)
        return len(p).to_bytes(2, 'big') + Datum.Command.value.to_bytes(1, 'big') + p


    def header(self, header):
        return None


    def message(self, msg, **kwargs):
        p = msgpack.dumps(self.message_data(msg, **kwargs))
        return len(p).to_bytes(2, 'big') + Datum.Message.value.to_bytes(1, 'big') + p


    def feed(self, packet):
        self.rbuff = self.rbuff + packet

        while len(self.rbuff):
            #print('rbuff:', self.rbuff)
            if not self.datum_len:
                self.datum_len = int.from_bytes(self.rbuff[:2], 'big')
                self.datum_type = int.from_bytes(self.rbuff[2:3], 'big')
                self.rbuff = self.rbuff[3:]

            if len(self.rbuff) >= self.datum_len:
                self.buffer.append((self.datum_type, self.rbuff[:self.datum_len]))
                self.rbuff = self.rbuff[self.datum_len:]
                self.datum_len = 0
                self.datum_type = None
            else:
                break


    def read(self):
        while len(self.buffer):
            dnum, p = self.buffer.pop(0)
            dtype = Datum(dnum)
            datum = msgpack.loads(p, raw=False)
            print('loads:', dtype, datum)
            yield datum


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
            self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
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

        self.nick = 'me'
        self.mode = Mode.msgpack
        self.sent_header = False
        self.address = address

        if sock:
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

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
        return self.receive_proto.mode


    @receive_mode.setter
    def receive_mode(self, mode):
        if mode == Mode.msgpack:
            self.receive_proto = Msgpack()
        elif mode == Mode.json:
            self.receive_proto = JSON()
        elif mode == Mode.text:
            self.receive_proto = PText()
        else:
            raise ValueError('Unknown protocol mode: {}'.format(mode))


    @property
    def send_mode(self):
        return self.send_proto.mode


    @send_mode.setter
    def send_mode(self, mode):
        if mode == Mode.msgpack:
            self.send_proto = Msgpack()
        elif mode == Mode.json:
            self.send_proto = JSON()
        elif mode == Mode.text:
            self.send_proto = PText()
        else:
            raise ValueError('Unknown protocol mode: {}'.format(mode))


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
            elif text.startswith('/nick'):
                name = text[6:]
                if len(name):
                    self.send_command('NICK', data=name)
                    self.nick = name
                    self.append_text('You are now known as {}\n'.format(name))
            elif text == '/text':
                self.send_command('TEXT')
                self.send_mode = Mode.text
                self.send_header_once()
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
            self.append_text('{} {}: {}\n'.format(timestamp(), self.nick, text))

            msg = self.send_proto.message(text, to=self.peer.name, From=str(self.address or ''))

            if _test_fragment:
                t = len(msg)
                h = t // 2

                self.peer.sendall(msg[:h])
                time.sleep(0.1)
                self.peer.sendall(msg[h:])
            else:
                self.peer.sendall(msg)


        # Prevent default handler from adding a newline to the input textbox
        return 'break'


    def send_command(self, cmd, data=None):
        message = self.send_proto.command(cmd, data=data)
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

        p = self.send_proto.header(data)
        if p is not None:
            self.peer.sendall(p)


    def update_peer_address(self, addr):
        self.peer.name = addr
        self.status_Label['text'] = 'Peer: ' + addr


    def process_header(self, header):
        self.update_peer_address(header['from'])


    def process_message(self, message):
        if 'to' in message and 'msg' not in message:
            self.process_header(message)

        elif 'cmd' in message:
            print('command:', message['cmd'], message['payload'])
            cmd = message['cmd']
            self.process_command(cmd, more=message['payload'])

        else:
            if message['from']:
                self.update_peer_address(message['from'])

            self.append_text('{} {}: {}\n'.format(timestamp(), self.peer.nick, message['msg']))


    def process_command(self, cmd, more=None):
        if cmd == 'JSON':
            self.receive_mode = Mode.json

            if more:
                self.process_packet(more)

        elif cmd == 'MPCK':
            self.receive_mode = Mode.msgpack

            if more:
                self.process_packet(more)

        elif cmd == 'TEXT':
            self.receive_mode = Mode.text

        elif cmd.startswith('NICK'):
            oldnick = self.peer.nick
            if more:
                nick = more.strip()
            else:
                nick = cmd[4:].strip()

            if nick not in ('me', '', self.nick):
                self.peer.nick = nick
                self.append_text('{} is now known as {}\n'.format(oldnick, self.peer.nick))
            else:
                self.append_text('{} tried to take the name {}, but that would be confusing.\n'.format(oldnick, nick))

        elif cmd == 'BYE ':
            self.disable('Disconnecting: Bye\n')
            self.disconnect()

        else:
            self.append_text('Unrecognized command: {}'.format(cmd))

    def process_packet(self, packet):
        self.receive_proto.feed(packet)

        i = self.receive_proto.read()
        for o in i:
            self.process_message(o)


    def eventChecker(self, *args): #could be (self, socket_fd, mask)
        try:
            try:
                packet = self.peer.recv(4096)
            except Exception as e:
                self.disable(str(e) + '\n')
                self.disconnect()
                traceback.print_exc()
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

        header = self.send_proto.first_packet
        self.peer.send(header)
        self.send_header_once()


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
