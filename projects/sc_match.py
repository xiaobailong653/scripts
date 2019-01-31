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

        parser.add_option("-t", "--test",
                          action="store_true",
                          dest="test",
                          default=False,
                          help="test")

        (options, args) = parser.parse_args(argv)

        if options.test:
            self.test()
            return

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
        data = [sheet.row_values(0)]
        for curr_row in range(1, num_rows):
            row = sheet.row_values(curr_row)
            if not row[0] and row[1] == "US":
                index = IdWorker().get_id()
                url = row[12]
                path = row[13][1:] if row[13].startswith("/") else row[13]
                sp_dir = os.path.join(wav_dir, path)
                sp_path = os.path.join(sp_dir, "sp.wav")
                if os.path.exists(sp_path):
                    video_path = self.download_youtube(url, index)
                    if video_path is not None:
                        tp_path = self.extract_audio(video_path)
                        tmp_csv = self.rundata(sp_path, tp_path)
                        if tmp_csv is not None:
                            dst_csv = os.path.join(self.output, "csvs/{}.csv".format(index))
                            os.rename(tmp_csv, dst_csv)
                            row[-2] = str(index)
                            row[-1] = dst_csv
                            print "Info: success: index={}".format(index)
                        else:
                            print "Error: make csv error, index={}".format(index)
                    else:
                        print "Error: tp file not exists, index={}".format(index)
                else:
                    print "Error: sp file not exists, index={}".format(index)
            data.append(row)
        self.save_result(data)

    def save_result(self, data):
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet(u'Sheet1', cell_overwrite_ok=True)
        for i in range(len(data)):
            for j in range(len(data[i])):
                sheet.write(i, j, data[i][j])
        workbook.save("{}/result.xls".format(self.output))

    def is_match(self, index):
        csv = os.path.join(self.output, "csvs/{}.csv".format(index))
        if os.path.exists(csv):
            return True
        return False

    def download_youtube(self, url, index):
        try:
            download_url = _real_main(url)
        except youtube_dl.utils.DownloadError:
            print "Error: get download url failed, index={}".format(index)
            return None
        try:
            r = requests.get(download_url)
            filename = "{}/videos/{}.mp4".format(self.output, index)
            if os.path.exists(filename):
                os.remove(filename)
            with open(filename, "w") as f:
                f.write(r.content)
        except Exception as ex:
            print "Error: download youtube video failed, index={}".format(index)
            return None
        return filename

    def mkdir_output(self, output):
        os.mkdir(output)
        os.mkdir("{}/videos/".format(output))
        os.mkdir("{}/csvs/".format(output))

    def rundata(self, sp, tp):
        csv_tmp = os.path.join(self.home, "tmp/csvs/")
        cmd = "{} -t {} -m {} {} -w csv --csv-basedir {} > /dev/null 2>&1".format(self.sonic, self.config, sp, tp, csv_tmp)
        print "Info: Run cmd: {}".format(cmd)
        os.system(cmd)
        sp_name = os.path.basename(sp)
        csv = os.path.join(csv_tmp, "{}_vamp_match-vamp-plugin_match_b_a.csv".format(sp_name[:-4]))
        if os.path.exists(csv):
            return csv
        return None

    def extract_audio(self, video):
        audio = "{}.wav".format(video.split(".")[0])
        if os.path.exists(audio):
            os.remove(audio)
        cmd = "{} -i {} -ab 160k -ac 2 -ar 44100 -vn {} > /dev/null 2>&1".format(self.ffmpeg, video, audio)
        print "Info: Run cmd: {}".format(cmd)
        os.system(cmd)
        if os.path.exists(audio):
            return audio
        return None

    def test(self):
        filename = "/home/sunlf/Documents/ScorePulse.xlsx"
        workbook = xlrd.open_workbook(filename)
        sheet = workbook.sheet_by_name(u'Sheet1')
        colspan = {}
        for item in sheet.merged_cells:
            for row in range(item[0], item[1]):
                for col in range(item[2], item[3]):
                    # 合并单元格的首格是有值的，所以在这里进行了去重
                    if (row, col) != (item[0], item[2]):
                        colspan.update({(row, col): (item[0], item[2])})

        num_rows = sheet.nrows
        for i in range(1, num_rows):
            row = sheet.row_values(i)
            for j in range(len(row)):
                if not row[j]:
                    pos = colspan.get((i, j))
                    if pos is not None:
                        row[j] = sheet.cell_value(*colspan.get((i, j)))
            print i, row
