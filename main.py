#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import importlib


def main(argv):
    if len(argv) > 1:
        if argv[1] in ["-h", "--help"]:
            usage()
        else:
            try:
                name = "projects.sc_%s" % argv[1]
                modular = importlib.import_module(name)
            except ImportError:
                print "Cannot find [%s], use -h for help." % argv[1]
                return
            classname = getattr(modular, "ScriptHandler")
            obj = classname()
            obj.parser_args(argv[1:])
    else:
        usage()


def usage():
    print "Usage: python {} [options]\n".format(__file__)
    print "Options:"

    projects = os.listdir("projects/")
    for project in projects:
        if project.startswith("sc_") and project.endswith(".py"):
            pro = project.split(".")[0]
            modular = importlib.import_module("projects.%s" % pro)
            print "\t%-20s%-50s" % (pro[3:], modular.ScriptHandler)


if __name__ == '__main__':
    main(sys.argv)
