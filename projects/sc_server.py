#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import getpass
from optparse import OptionParser
import tornado.ioloop
import tornado.web

SERVER_PROT = 9701


class ScriptHandler(object):
    """部署virtualenv"""
    def __init__(self):
        pass

    def parser_args(self, argv):
        parser = OptionParser()

        parser.add_option("", "--start",
                          action="store_true",
                          dest="start",
                          default=False,
                          help="Start tornado server.")

        parser.add_option("", "--port",
                          action="store",
                          dest="port",
                          default=False,
                          help="Set server port.")

        (options, args) = parser.parse_args(argv)

        if options.start:
            port = int(options.port) if options.port else SERVER_PROT
            self.start_server(port)

    def start_server(self, port):
        app = tornado.web.Application(self.app_list())
        app.listen(port)
        print "Server listening on {}......".format(port)
        tornado.ioloop.IOLoop.current().start()

    def app_list(self):
        return [
            (r"/pull/code/(.*)", PullCodeHandler),
        ]


class PullCodeHandler(tornado.web.RequestHandler):
    def get(self, path):
        workspace = self._get_workspace(path)
        print workspace
        os.chdir(workspace)
        cmd = "git pull"
        os.system(cmd)
        self.write("ok")
        self.finish()

    def _get_workspace(self, name):
        user = getpass.getuser()
        return "/home/{}/workspace/{}".format(user, name)

