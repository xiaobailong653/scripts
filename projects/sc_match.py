#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import xlrd
import xlwt
import glob
import requests
from optparse import OptionParser
from youtube_dl import _real_main
from utils.u_file import FileHandler
from utils.u_snowflake import IdWorker


class ScriptHandler(object):
    """部署virtualenv"""
    def __init__(self):
        self.home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sonic = "/usr/bin/sonic-annotator"
        self.ffmpeg = "/usr/bin/ffmpeg"
        self.config = os.path.join(self.home, "configs/tp_match_sp.txt")

    def parser_args(self, argv):
        parser = OptionParser()

        parser.add_option("-e", "--excel",
                          action="store",
                          dest="excel",
                          default=False,
                          help="Input excel path")

        parser.add_option("-w", "--wav",
                          action="store",
                          dest="wav",
                          default=False,
                          help="Input wav dir path")

        parser.add_option("-o", "--output",
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
                video_path = self.download_youtube(url, curr_row+1)
                tp_path = self.extract_audio(video_path)
                tmp_csv = self.rundata(sp_path, tp_path)
                if tmp_csv is not None:
                    dst_csv = os.path.join(self.output, "csvs/{}.csv".format(curr_row+1))
                else:
                    print "Error: make csv error, index={}".format(curr_row+1)

    def download_youtube(self, url, index):
        download_url = _real_main(url)
        r = requests.get(download_url)
        filename = "{}/videos/{}_{}.mp4".format(self.output, index, IdWorker().get_id())
        with open(filename, "w") as f:
            f.write(r.content)
        return filename

    def mkdir_output(self, output):
        os.mkdir(output)
        os.mkdir("{}/videos/".format(output))
        os.mkdir("{}/csvs/".format(output))

    def rundata(self, sp, tp):
        csv_tmp = os.path.join(self.home, "tmp")
        cmd = "{} -t {} -m {} {} -w csv --csv-basedir {}/csvs/ > /dev/null 2>&1".format(self.sonic, self.config, sp, tp, csv_tmp)
        print "Info: Run cmd: {}".format(cmd)
        os.system(cmd)
        sp_name = os.path.basename(sp)
        csv = os.path.join(csv_tmp, "{}_vamp_match-vamp-plugin_match_b_a.csv".format(sp_name[:-4]))
        if os.path.exists(csv):
            return csv
        return None

    def extract_audio(self, video):
        audio = "{}.wav".format(video.split(".")[0])
        cmd = "{} -i {} -ab 160k -ac 2 -ar 44100 -vn {} > /dev/null 2>&1".format(self.ffmpeg, video, audio)
        print "Info: Run cmd: {}".format(cmd)
        os.system(cmd)
        if os.path.exists(audio):
            return audio
        return None
