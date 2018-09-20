import datetime
import socket
import struct

def timestamp():
    return '[' + datetime.datetime.now().strftime('%X') + ']'

class Socket(socket.socket):
    '''Wrap the python socket.socket class with extra method(s)'''

    def __init__(self, *args, **kwargs):
        socket.socket.__init__(self, *args, **kwargs)


    def abort(self, data=None):
        '''Abort a connection (RST) and optionally send a final transmission.

        Use for unrecoverable protocol errors.'''
        l_onoff = 1
        l_linger = 0
        self.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                     struct.pack('ii', l_onoff, l_linger))

        try:
            if data:
                self.sendall(data)
        finally:
            self.close()
