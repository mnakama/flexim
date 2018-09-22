'''Modified from https://pastebin.com/mWfDm7eZ

More info: https://stackoverflow.com/questions/3402110/hyperlink-in-tkinter-text-widget#3404849'''

import os
import sys
from tkinter import *

class Hyperlink:
    def __init__(self, text):

        self.text = text

        self.text.tag_config("hyper", foreground="blue", underline=1)

        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)

        self.reset()


    def reset(self):
        self.links = {}


    @staticmethod
    def follow_link(link, *args):
        print('follow_link: ', link)
        pid = os.fork()
        if pid == 0: return

        browsers = [
            'xdg-open',
            'firefox',
            'chromium',
            'chrome',
            'google-chrome-stable',
            'uzbl',
            'surf',
        ]

        try:
            for program in browsers:
                try:
                    os.execlp(program, program, link)
                except FileNotFoundError:
                    pass  # Try the next one
        finally:
            print('Failed to launch web browser')
            # Should be a sys.exit(1) here, but xcb complains that we're
            # multi-threading and crashes the program if we don't successfully
            # exec something, so I use /bin/false for now
            os.execl('/bin/false', '/bin/false')



    def add(self, index, text, action=None):
        # add an action to the manager.  returns tags to use in
        # associated text widget

        if not action:
            action = Hyperlink.follow_link

        tag = "hyper-%d" % len(self.links)
        self.links[tag] = (text, action)

        self.text.insert(index, text, ('hyper', tag))


    def _enter(self, event):
        self.text.config(cursor="hand2")


    def _leave(self, event):
        self.text.config(cursor="")


    def _click(self, event):
        for tag in self.text.tag_names(CURRENT):
            if tag[:6] == "hyper-":
                self.links[tag][1](self.links[tag][0])
                return
