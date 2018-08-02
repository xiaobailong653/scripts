#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from optparse import OptionParser

from utils.u_file import FileHandler


class ScriptHandler(object):
    """部署virtualenv"""
    def __init__(self):
        pass

    def parser_args(self, argv):
        parser = OptionParser()

        parser.add_option("", "--build-env",
                          action="store_true",
                          dest="build_env",
                          default=False,
                          help="部署virtualenv和virtualenvwrapper环境。")

        (options, args) = parser.parse_args(argv)

        if options.build_env:
            self.build_env()

    def build_env(self):
        FileHandler.shell_execute("build_virtualenv.sh")
        print "Build success."
