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

        parser.add_option("", "--input",
                          action="store",
                          dest="input",
                          default=False,
                          help="Input path")

        parser.add_option("", "--output",
                          action="store",
                          dest="output",
                          default=False,
                          help="output")

        (options, args) = parser.parse_args(argv)

        if options.input and options.output:
            if not os.path.isdir(options.output):
                os.mkdir(options.output)
            self.match_handler(options.input, options.output)
        else:
            print "Miss args, use --input and --output set args."
            return

    def match_handler(self, input_path, output_path):
        print "this is match_handler"
        print input_path
        print output_path
