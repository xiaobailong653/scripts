# -*- coding: utf-8 -*-
from youtube_dl import _real_main

print(_real_main("https://www.youtube.com/watch?v=dTCcegIiKXE"))

__all__ = ['main', 'YoutubeDL', 'gen_extractors', 'list_extractors']
