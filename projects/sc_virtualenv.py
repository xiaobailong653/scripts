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

        parser.add_option("", "--show-cmd",
                          action="store_true",
                          dest="show_cmd",
                          default=False,
                          help="显示virtualenv的操作命令。")

        (options, args) = parser.parse_args(argv)

        if options.build_env:
            self.build_env()
        elif options.show_cmd:
            self.show_cmd()

    def build_env(self):
        FileHandler.shell_execute("build_virtualenv.sh")
        print "Build success."

    def show_cmd(self):
        cmds = [
          ("mkvirtualenv [env name]", "创建虚拟环境"),
          ("mkproject [env name]", "创建项目+环境"),
          ("workon [env name]", "切换虚拟环境"),
          ("deactivate", "退出虚拟环境"),
          ("rmvirtualenv [env name]", "删除虚拟环境"),
          ("lsvirtualenv", "列出所有环境"),
          ("cpvirtualenv", "复制环境"),
          ("cdsitepackages", "cd到当前环境的site-packages目录"),
          ("lssitepackages", "列出当前环境中site-packages内容"),
          ("setvirtualenvproject", "绑定现存的项目和环境"),
          ("wipeenv", "清除环境内所有第三方包"),
        ]

        for cmd in cmds:
            print "\t%-30s%-70s" % (cmd[0], cmd[1])

