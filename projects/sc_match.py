#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import xlrd
import xlwt
from optparse import OptionParser
from youtube_dl import _real_main
from utils.u_file import FileHandler
from utils.u_snowflake import IdWorker


class ScriptHandler(object):
    """部署virtualenv"""
    def __init__(self):
        self.home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sonic = os.path.join(self.home, "shells/sonic-annotator")
        self.config = os.path.join(self.home, "configs/tp_match_sp.txt")

    def parser_args(self, argv):
        parser = OptionParser()

        parser.add_option("", "--excel",
                          action="store",
                          dest="excel",
                          default=False,
                          help="Input excel path")

        parser.add_option("", "--wav",
                          action="store",
                          dest="wav",
                          default=False,
                          help="Input wav dir path")

        parser.add_option("", "--output",
                          action="store",
                          dest="output",
                          default=False,
                          help="Output dir path")

        (options, args) = parser.parse_args(argv)

        if options.excel and options.wav and options.output:
            if not os.path.exists(options.output):
                self.mkdir_output(options.output)
            self.output = options.output
            self.match_handler(options.excel, options.wav)
        else:
            print "Miss args, use --excel, --wav and --output set args."
            return

    def match_handler(self, excel, wav_dir):
        workbook = xlrd.open_workbook(excel)
        sheet = workbook.sheet_by_name(u'Sheet1')
        num_rows = sheet.nrows
        for curr_row in range(1, num_rows):
            row = sheet.row_values(curr_row)
            if row[0]:
                url = row[11]
                path = row[12][1:] if row[12].startswith("/") else row[12]
                sp_dir = os.path.join(wav_dir, row[12])
                sp_path = os.path.join(sp_dir, "sp.wav")
                # tp_path = self.download_youtube(url)
                tp_path = "/home/sunlf/tmp/wavs/tp.wav"
                self.rundata(sp_path, tp_path)

    def download_youtube(self, url):
        # download_url = _real_main(url)
        # r = requests.get(download_url)
        filename = "{}/videos/{}.mp4".format(self.output, IdWorker().get_id())
        # with open(filename, "w") as f:
        #     f.write(r.content)
        return filename

    def mkdir_output(self, output):
        os.mkdir(output)
        os.mkdir("{}/videos/".format(output))
        os.mkdir("{}/csvs/".format(output))

    def rundata(self, sp, tp):
        cmd = "/usr/bin/sonic-annotator -t {} -m {} {} -w csv --csv-basedir {}/csvs/".format(self.config, tp, sp, self.output)
        print cmd
        os.system(cmd)
