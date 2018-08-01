#!/usr/bin/env python
# -*- coding: utf-8 -*-
from optparse import OptionParser


class ScriptHandler(object):
    def __init__(self):
        pass

    def __repr__(self):
        print "virtual"

    def parser_args(self, argv):
        parser = OptionParser()

        parser.add_option("", "--init-env",
                          action="store_true",
                          dest="init_env",
                          default=False,
                          help="Init env.")

        (options, args) = parser.parse_args(argv)

        if options.init_env:
            print "virtual env init"
