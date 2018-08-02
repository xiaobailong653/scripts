#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os


class FileHandler(object):
    @classmethod
    def root_dir(cls):

        return os.path.dirname(os.path.dirname(__file__))

    @classmethod
    def shell_file(cls, name):
        root_dir = cls.root_dir()
        file_path = os.path.join(root_dir, "shells/{}".format(name))
        return file_path

    @classmethod
    def shell_execute(cls, name):
        file_path = cls.shell_file(name)
        os.system(file_path)
