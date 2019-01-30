#!/usr/bin/env python
# coding: utf-8

from __future__ import absolute_import, unicode_literals

import collections
import contextlib
import copy
import datetime
import errno
import fileinput
import io
import itertools
import json
import locale
import operator
import os
import platform
import re
import shutil
import subprocess
import socket
import sys

import tokenize
import traceback
import random

from string import ascii_letters

from .compat import (
    compat_basestring,
    compat_cookiejar,
    compat_get_terminal_size,
    compat_http_client,
    compat_kwargs,
    compat_numeric_types,
    compat_os_name,
    compat_str,
    compat_tokenize_tokenize,
    compat_urllib_error,
    compat_urllib_request,
    compat_urllib_request_DataHandler,
)
from .utils import (
    age_restricted,
    args_to_str,
    ContentTooShortError,
    date_from_str,
    DateRange,
    DEFAULT_OUTTMPL,
    determine_ext,
    determine_protocol,
    DownloadError,
    encode_compat_str,
    encodeFilename,
    error_to_compat_str,
    expand_path,
    ExtractorError,
    format_bytes,
    formatSeconds,
    GeoRestrictedError,
    int_or_none,
    ISO3166Utils,
    locked_file,
    make_HTTPS_handler,
    MaxDownloadsReached,
    orderedSet,
    PagedList,
    parse_filesize,
    PerRequestProxyHandler,
    platform_name,
    PostProcessingError,
    preferredencoding,
    prepend_extension,
    register_socks_protocols,
    render_table,
    replace_extension,
    SameFileError,
    sanitize_filename,
    sanitize_path,
    sanitize_url,
    sanitized_Request,
    std_headers,
    subtitles_filename,
    UnavailableVideoError,
    url_basename,
    version_tuple,
    write_json_file,
    write_string,
    YoutubeDLCookieJar,
    YoutubeDLCookieProcessor,
    YoutubeDLHandler,
)
from .cache import Cache
from .extractor import get_info_extractor, gen_extractor_classes, _LAZY_LOADER
from .extractor.openload import PhantomJSwrapper


from .version import __version__

if compat_os_name == 'nt':
    import ctypes


class YoutubeDL(object):

    _NUMERIC_FIELDS = set((
        'width', 'height', 'tbr', 'abr', 'asr', 'vbr', 'fps', 'filesize', 'filesize_approx',
        'timestamp', 'upload_year', 'upload_month', 'upload_day',
        'duration', 'view_count', 'like_count', 'dislike_count', 'repost_count',
        'average_rating', 'comment_count', 'age_limit',
        'start_time', 'end_time',
        'chapter_number', 'season_number', 'episode_number',
        'track_number', 'disc_number', 'release_year',
        'playlist_index',
    ))

    params = None
    _ies = []
    _pps = []
    _download_retcode = None
    _num_downloads = None
    _screen_file = None

    def __init__(self, params=None, auto_init=True):
        """Create a FileDownloader object with the given options."""
        if params is None:
            params = {}
        self._ies = []
        self._ies_instances = {}
        self._pps = []
        self._progress_hooks = []
        self._download_retcode = 0
        self._num_downloads = 0
        self._screen_file = [sys.stdout, sys.stderr][params.get('logtostderr', False)]
        self._err_file = sys.stderr
        self.params = {
            # Default parameters
            'nocheckcertificate': False,
        }
        self.params.update(params)
        self.cache = Cache(self)

        def check_deprecated(param, option, suggestion):
            if self.params.get(param) is not None:
                self.report_warning(
                    '%s is deprecated. Use %s instead.' % (option, suggestion))
                return True
            return False

        if check_deprecated('cn_verification_proxy', '--cn-verification-proxy', '--geo-verification-proxy'):
            if self.params.get('geo_verification_proxy') is None:
                self.params['geo_verification_proxy'] = self.params['cn_verification_proxy']

        check_deprecated('autonumber_size', '--autonumber-size', 'output template with %(autonumber)0Nd, where N in the number of digits')
        check_deprecated('autonumber', '--auto-number', '-o "%(autonumber)s-%(title)s.%(ext)s"')
        check_deprecated('usetitle', '--title', '-o "%(title)s-%(id)s.%(ext)s"')

        if params.get('bidi_workaround', False):
            try:
                import pty
                master, slave = pty.openpty()
                width = compat_get_terminal_size().columns
                if width is None:
                    width_args = []
                else:
                    width_args = ['-w', str(width)]
                sp_kwargs = dict(
                    stdin=subprocess.PIPE,
                    stdout=slave,
                    stderr=self._err_file)
                try:
                    self._output_process = subprocess.Popen(
                        ['bidiv'] + width_args, **sp_kwargs
                    )
                except OSError:
                    self._output_process = subprocess.Popen(
                        ['fribidi', '-c', 'UTF-8'] + width_args, **sp_kwargs)
                self._output_channel = os.fdopen(master, 'rb')
            except OSError as ose:
                if ose.errno == errno.ENOENT:
                    self.report_warning('Could not find fribidi executable, ignoring --bidi-workaround . Make sure that  fribidi  is an executable file in one of the directories in your $PATH.')
                else:
                    raise

        if (sys.platform != 'win32' and
                sys.getfilesystemencoding() in ['ascii', 'ANSI_X3.4-1968'] and
                not params.get('restrictfilenames', False)):
            # Unicode filesystem API will throw errors (#1474, #13027)
            self.report_warning(
                'Assuming --restrict-filenames since file system encoding '
                'cannot encode all characters. '
                'Set the LC_ALL environment variable to fix this.')
            self.params['restrictfilenames'] = True

        if isinstance(params.get('outtmpl'), bytes):
            self.report_warning(
                'Parameter outtmpl is bytes, but should be a unicode string. '
                'Put  from __future__ import unicode_literals  at the top of your code file or consider switching to Python 3.x.')

        self._setup_opener()

        if auto_init:
            self.print_debug_header()
            self.add_default_info_extractors()

        for pp_def_raw in self.params.get('postprocessors', []):
            pp_class = get_postprocessor(pp_def_raw['key'])
            pp_def = dict(pp_def_raw)
            del pp_def['key']
            pp = pp_class(self, **compat_kwargs(pp_def))
            self.add_post_processor(pp)

        for ph in self.params.get('progress_hooks', []):
            self.add_progress_hook(ph)

        register_socks_protocols()

    def warn_if_short_id(self, argv):
        # short YouTube ID starting with dash?
        idxs = [
            i for i, a in enumerate(argv)
            if re.match(r'^-[0-9A-Za-z_-]{10}$', a)]
        if idxs:
            correct_argv = (
                ['youtube-dl'] +
                [a for i, a in enumerate(argv) if i not in idxs] +
                ['--'] + [argv[i] for i in idxs]
            )
            self.report_warning(
                'Long argument string detected. '
                'Use -- to separate parameters and URLs, like this:\n%s\n' %
                args_to_str(correct_argv))

    def add_info_extractor(self, ie):
        """Add an InfoExtractor object to the end of the list."""
        self._ies.append(ie)
        if not isinstance(ie, type):
            self._ies_instances[ie.ie_key()] = ie
            ie.set_downloader(self)

    def get_info_extractor(self, ie_key):
        """
        Get an instance of an IE with name ie_key, it will try to get one from
        the _ies list, if there's no instance it will create a new one and add
        it to the extractor list.
        """
        ie = self._ies_instances.get(ie_key)
        if ie is None:
            ie = get_info_extractor(ie_key)()
            self.add_info_extractor(ie)
        return ie





    def add_default_info_extractors(self):
        """
        Add the InfoExtractors returned by gen_extractors to the end of the list
        """
        for ie in gen_extractor_classes():
            self.add_info_extractor(ie)

    def add_post_processor(self, pp):
        """Add a PostProcessor object to the end of the chain."""
        self._pps.append(pp)
        pp.set_downloader(self)

    def add_progress_hook(self, ph):
        """Add the progress hook (currently only for the file downloader)"""
        self._progress_hooks.append(ph)

    def _bidi_workaround(self, message):
        if not hasattr(self, '_output_channel'):
            return message

        assert hasattr(self, '_output_process')
        assert isinstance(message, compat_str)
        line_count = message.count('\n') + 1
        self._output_process.stdin.write((message + '\n').encode('utf-8'))
        self._output_process.stdin.flush()
        res = ''.join(self._output_channel.readline().decode('utf-8')
                      for _ in range(line_count))
        return res[:-len('\n')]

    def to_screen(self, message, skip_eol=False):
        """Print message to stdout if not in quiet mode."""
        return self.to_stdout(message, skip_eol, check_quiet=True)

    def _write_string(self, s, out=None):
        write_string(s, out=out, encoding=self.params.get('encoding'))

    def to_stdout(self, message, skip_eol=False, check_quiet=False):
        """Print message to stdout if not in quiet mode."""
        if self.params.get('logger'):
            self.params['logger'].debug(message)
        elif not check_quiet or not self.params.get('quiet', False):
            message = self._bidi_workaround(message)
            terminator = ['\n', ''][skip_eol]
            output = message + terminator

            self._write_string(output, self._screen_file)

    def to_stderr(self, message):
        """Print message to stderr."""
        assert isinstance(message, compat_str)
        if self.params.get('logger'):
            self.params['logger'].error(message)
        else:
            message = self._bidi_workaround(message)
            output = message + '\n'
            self._write_string(output, self._err_file)

    def to_console_title(self, message):
        if not self.params.get('consoletitle', False):
            return
        if compat_os_name == 'nt':
            if ctypes.windll.kernel32.GetConsoleWindow():
                # c_wchar_p() might not be necessary if `message` is
                # already of type unicode()
                ctypes.windll.kernel32.SetConsoleTitleW(ctypes.c_wchar_p(message))
        elif 'TERM' in os.environ:
            self._write_string('\033]0;%s\007' % message, self._screen_file)

    def save_console_title(self):
        if not self.params.get('consoletitle', False):
            return
        if self.params.get('simulate', False):
            return
        if compat_os_name != 'nt' and 'TERM' in os.environ:
            # Save the title on stack
            self._write_string('\033[22;0t', self._screen_file)

    def restore_console_title(self):
        if not self.params.get('consoletitle', False):
            return
        if self.params.get('simulate', False):
            return
        if compat_os_name != 'nt' and 'TERM' in os.environ:
            # Restore the title from stack
            self._write_string('\033[23;0t', self._screen_file)

    def __enter__(self):
        self.save_console_title()
        return self

    def __exit__(self, *args):
        self.restore_console_title()

        if self.params.get('cookiefile') is not None:
            self.cookiejar.save(ignore_discard=True, ignore_expires=True)

    def trouble(self, message=None, tb=None):
        """Determine action to take when a download problem appears.

        Depending on if the downloader has been configured to ignore
        download errors or not, this method may throw an exception or
        not when errors are found, after printing the message.

        tb, if given, is additional traceback information.
        """
        if message is not None:
            self.to_stderr(message)
        if self.params.get('verbose'):
            if tb is None:
                if sys.exc_info()[0]:  # if .trouble has been called from an except block
                    tb = ''
                    if hasattr(sys.exc_info()[1], 'exc_info') and sys.exc_info()[1].exc_info[0]:
                        tb += ''.join(traceback.format_exception(*sys.exc_info()[1].exc_info))
                    tb += encode_compat_str(traceback.format_exc())
                else:
                    tb_data = traceback.format_list(traceback.extract_stack())
                    tb = ''.join(tb_data)
            self.to_stderr(tb)
        if not self.params.get('ignoreerrors', False):
            if sys.exc_info()[0] and hasattr(sys.exc_info()[1], 'exc_info') and sys.exc_info()[1].exc_info[0]:
                exc_info = sys.exc_info()[1].exc_info
            else:
                exc_info = sys.exc_info()
            raise DownloadError(message, exc_info)
        self._download_retcode = 1

    def report_warning(self, message):
        '''
        Print the message to stderr, it will be prefixed with 'WARNING:'
        If stderr is a tty file the 'WARNING:' will be colored
        '''
        if self.params.get('logger') is not None:
            self.params['logger'].warning(message)
        else:
            if self.params.get('no_warnings'):
                return
            if not self.params.get('no_color') and self._err_file.isatty() and compat_os_name != 'nt':
                _msg_header = '\033[0;33mWARNING:\033[0m'
            else:
                _msg_header = 'WARNING:'
            warning_message = '%s %s' % (_msg_header, message)
            self.to_stderr(warning_message)

    def report_error(self, message, tb=None):
        '''
        Do the same as trouble, but prefixes the message with 'ERROR:', colored
        in red if stderr is a tty file.
        '''
        if not self.params.get('no_color') and self._err_file.isatty() and compat_os_name != 'nt':
            _msg_header = '\033[0;31mERROR:\033[0m'
        else:
            _msg_header = 'ERROR:'
        error_message = '%s %s' % (_msg_header, message)
        self.trouble(error_message, tb)

    def _match_entry(self, info_dict, incomplete):
        """ Returns None iff the file should be downloaded """
        video_title = info_dict.get('title', info_dict.get('id', 'video'))
        if 'title' in info_dict:
            # This can happen when we're just evaluating the playlist
            title = info_dict['title']
            matchtitle = self.params.get('matchtitle', False)
            if matchtitle:
                if not re.search(matchtitle, title, re.IGNORECASE):
                    return '"' + title + '" title did not match pattern "' + matchtitle + '"'
            rejecttitle = self.params.get('rejecttitle', False)
            if rejecttitle:
                if re.search(rejecttitle, title, re.IGNORECASE):
                    return '"' + title + '" title matched reject pattern "' + rejecttitle + '"'
        date = info_dict.get('upload_date')
        if date is not None:
            dateRange = self.params.get('daterange', DateRange())
            if date not in dateRange:
                return '%s upload date is not in range %s' % (date_from_str(date).isoformat(), dateRange)
        view_count = info_dict.get('view_count')
        if view_count is not None:
            min_views = self.params.get('min_views')
            if min_views is not None and view_count < min_views:
                return 'Skipping %s, because it has not reached minimum view count (%d/%d)' % (video_title, view_count, min_views)
            max_views = self.params.get('max_views')
            if max_views is not None and view_count > max_views:
                return 'Skipping %s, because it has exceeded the maximum view count (%d/%d)' % (video_title, view_count, max_views)
        if age_restricted(info_dict.get('age_limit'), self.params.get('age_limit')):
            return 'Skipping "%s" because it is age restricted' % video_title
        if self.in_download_archive(info_dict):
            return '%s has already been recorded in archive' % video_title

        if not incomplete:
            match_filter = self.params.get('match_filter')
            if match_filter is not None:
                ret = match_filter(info_dict)
                if ret is not None:
                    return ret
        return None

    @staticmethod
    def add_extra_info(info_dict, extra_info):
        '''Set the keys from extra_info in info dict if they are missing'''
        for key, value in extra_info.items():
            info_dict.setdefault(key, value)

    def extract_info(self, url, download=False, ie_key=None, extra_info={},
                     process=True, force_generic_extractor=False):
        myurl = ""
        if not ie_key and force_generic_extractor:
            ie_key = 'Generic'
        if ie_key:
            ies = [self.get_info_extractor(ie_key)]
        else:
            ies = self._ies
        for ie in ies:
            if not ie.suitable(url):
                continue
            ie = self.get_info_extractor(ie.ie_key())
            if not ie.working():
                self.report_warning('The program functionality for this site has been marked as broken, '
                                    'and will probably not work.')
            try:
                ie_result = ie.extract(url)
                if ie_result is None:  # Finished already (backwards compatibility; listformats and friends should be moved here)
                    break
                for mydic in ie_result["formats"]:
                    if mydic["ext"] == "mp4" and mydic["acodec"] != "none":
                        myurl = mydic["url"]
                        break
                break
            except GeoRestrictedError as e:
                msg = e.msg
                if e.countries:
                    msg += '\nThis video is available in %s.' % ', '.join(
                        map(ISO3166Utils.short2full, e.countries))
                msg += '\nYou might want to use a VPN or a proxy server (with --proxy) to workaround.'
                self.report_error(msg)
                break
            except ExtractorError as e:  # An error we somewhat expected
                self.report_error(compat_str(e), e.format_traceback())
                break
            except MaxDownloadsReached:
                raise
            except Exception as e:
                if self.params.get('ignoreerrors', False):
                    self.report_error(error_to_compat_str(e), tb=encode_compat_str(traceback.format_exc()))
                    break
                else:
                    raise
        else:
            self.report_error('no suitable InfoExtractor for URL %s' % url)
        return myurl
    def add_default_extra_info(self, ie_result, ie, url):
        self.add_extra_info(ie_result, {
            'extractor': ie.IE_NAME,
            'webpage_url': url,
            'webpage_url_basename': url_basename(url),
            'extractor_key': ie.ie_key(),
        })


    def process_ie_result(self, ie_result, download=True, extra_info={}):
        """
        Take the result of the ie(may be modified) and resolve all unresolved
        references (URLs, playlist items).

        It will also download the videos if 'download'.
        Returns the resolved ie_result.
        """
        result_type = ie_result.get('_type', 'video')

        if result_type in ('url', 'url_transparent'):
            ie_result['url'] = sanitize_url(ie_result['url'])
            extract_flat = self.params.get('extract_flat', False)
            if ((extract_flat == 'in_playlist' and 'playlist' in extra_info) or
                    extract_flat is True):
                if self.params.get('forcejson', False):
                    self.to_stdout(json.dumps(ie_result))
                return ie_result

        if result_type == 'video':
            self.add_extra_info(ie_result, extra_info)
            return self.process_video_result(ie_result, download=download)
        elif result_type == 'url':
            # We have to add extra_info to the results because it may be
            # contained in a playlist
            return self.extract_info(ie_result['url'],
                                     download,
                                     ie_key=ie_result.get('ie_key'),
                                     extra_info=extra_info)
        elif result_type == 'url_transparent':
            # Use the information from the embedding page
            info = self.extract_info(
                ie_result['url'], ie_key=ie_result.get('ie_key'),
                extra_info=extra_info, download=False, process=False)

            # extract_info may return None when ignoreerrors is enabled and
            # extraction failed with an error, don't crash and return early
            # in this case
            if not info:
                return info

            force_properties = dict(
                (k, v) for k, v in ie_result.items() if v is not None)
            for f in ('_type', 'url', 'id', 'extractor', 'extractor_key', 'ie_key'):
                if f in force_properties:
                    del force_properties[f]
            new_result = info.copy()
            new_result.update(force_properties)

            # Extracted info may not be a video result (i.e.
            # info.get('_type', 'video') != video) but rather an url or
            # url_transparent. In such cases outer metadata (from ie_result)
            # should be propagated to inner one (info). For this to happen
            # _type of info should be overridden with url_transparent. This
            # fixes issue from https://github.com/rg3/youtube-dl/pull/11163.
            if new_result.get('_type') == 'url':
                new_result['_type'] = 'url_transparent'

            return self.process_ie_result(
                new_result, download=download, extra_info=extra_info)
        elif result_type in ('playlist', 'multi_video'):
            # We process each entry in the playlist
            playlist = ie_result.get('title') or ie_result.get('id')
            self.to_screen('[download] Downloading playlist: %s' % playlist)

            playlist_results = []

            playliststart = self.params.get('playliststart', 1) - 1
            playlistend = self.params.get('playlistend')
            # For backwards compatibility, interpret -1 as whole list
            if playlistend == -1:
                playlistend = None

            playlistitems_str = self.params.get('playlist_items')
            playlistitems = None
            if playlistitems_str is not None:
                def iter_playlistitems(format):
                    for string_segment in format.split(','):
                        if '-' in string_segment:
                            start, end = string_segment.split('-')
                            for item in range(int(start), int(end) + 1):
                                yield int(item)
                        else:
                            yield int(string_segment)
                playlistitems = orderedSet(iter_playlistitems(playlistitems_str))

            ie_entries = ie_result['entries']

            def make_playlistitems_entries(list_ie_entries):
                num_entries = len(list_ie_entries)
                return [
                    list_ie_entries[i - 1] for i in playlistitems
                    if -num_entries <= i - 1 < num_entries]

            def report_download(num_entries):
                self.to_screen(
                    '[%s] playlist %s: Downloading %d videos' %
                    (ie_result['extractor'], playlist, num_entries))

            if isinstance(ie_entries, list):
                n_all_entries = len(ie_entries)
                if playlistitems:
                    entries = make_playlistitems_entries(ie_entries)
                else:
                    entries = ie_entries[playliststart:playlistend]
                n_entries = len(entries)
                self.to_screen(
                    '[%s] playlist %s: Collected %d video ids (downloading %d of them)' %
                    (ie_result['extractor'], playlist, n_all_entries, n_entries))
            elif isinstance(ie_entries, PagedList):
                if playlistitems:
                    entries = []
                    for item in playlistitems:
                        entries.extend(ie_entries.getslice(
                            item - 1, item
                        ))
                else:
                    entries = ie_entries.getslice(
                        playliststart, playlistend)
                n_entries = len(entries)
                report_download(n_entries)
            else:  # iterable
                if playlistitems:
                    entries = make_playlistitems_entries(list(itertools.islice(
                        ie_entries, 0, max(playlistitems))))
                else:
                    entries = list(itertools.islice(
                        ie_entries, playliststart, playlistend))
                n_entries = len(entries)
                report_download(n_entries)

            if self.params.get('playlistreverse', False):
                entries = entries[::-1]

            if self.params.get('playlistrandom', False):
                random.shuffle(entries)

            x_forwarded_for = ie_result.get('__x_forwarded_for_ip')

            for i, entry in enumerate(entries, 1):
                self.to_screen('[download] Downloading video %s of %s' % (i, n_entries))
                # This __x_forwarded_for_ip thing is a bit ugly but requires
                # minimal changes
                if x_forwarded_for:
                    entry['__x_forwarded_for_ip'] = x_forwarded_for
                extra = {
                    'n_entries': n_entries,
                    'playlist': playlist,
                    'playlist_id': ie_result.get('id'),
                    'playlist_title': ie_result.get('title'),
                    'playlist_uploader': ie_result.get('uploader'),
                    'playlist_uploader_id': ie_result.get('uploader_id'),
                    'playlist_index': i + playliststart,
                    'extractor': ie_result['extractor'],
                    'webpage_url': ie_result['webpage_url'],
                    'webpage_url_basename': url_basename(ie_result['webpage_url']),
                    'extractor_key': ie_result['extractor_key'],
                }

                reason = self._match_entry(entry, incomplete=True)
                if reason is not None:
                    self.to_screen('[download] ' + reason)
                    continue

                entry_result = self.process_ie_result(entry,
                                                      download=download,
                                                      extra_info=extra)
                playlist_results.append(entry_result)
            ie_result['entries'] = playlist_results
            self.to_screen('[download] Finished downloading playlist: %s' % playlist)
            return ie_result
        elif result_type == 'compat_list':
            self.report_warning(
                'Extractor %s returned a compat_list result. '
                'It needs to be updated.' % ie_result.get('extractor'))

            def _fixup(r):
                self.add_extra_info(
                    r,
                    {
                        'extractor': ie_result['extractor'],
                        'webpage_url': ie_result['webpage_url'],
                        'webpage_url_basename': url_basename(ie_result['webpage_url']),
                        'extractor_key': ie_result['extractor_key'],
                    }
                )
                return r
            ie_result['entries'] = [
                self.process_ie_result(_fixup(r), download, extra_info)
                for r in ie_result['entries']
            ]
            return ie_result
        else:
            raise Exception('Invalid result type: %s' % result_type)

    def _build_format_filter(self, filter_spec):
        " Returns a function to filter the formats according to the filter_spec "

        OPERATORS = {
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
            '=': operator.eq,
            '!=': operator.ne,
        }
        operator_rex = re.compile(r'''(?x)\s*
            (?P<key>width|height|tbr|abr|vbr|asr|filesize|filesize_approx|fps)
            \s*(?P<op>%s)(?P<none_inclusive>\s*\?)?\s*
            (?P<value>[0-9.]+(?:[kKmMgGtTpPeEzZyY]i?[Bb]?)?)
            $
            ''' % '|'.join(map(re.escape, OPERATORS.keys())))
        m = operator_rex.search(filter_spec)
        if m:
            try:
                comparison_value = int(m.group('value'))
            except ValueError:
                comparison_value = parse_filesize(m.group('value'))
                if comparison_value is None:
                    comparison_value = parse_filesize(m.group('value') + 'B')
                if comparison_value is None:
                    raise ValueError(
                        'Invalid value %r in format specification %r' % (
                            m.group('value'), filter_spec))
            op = OPERATORS[m.group('op')]

        if not m:
            STR_OPERATORS = {
                '=': operator.eq,
                '^=': lambda attr, value: attr.startswith(value),
                '$=': lambda attr, value: attr.endswith(value),
                '*=': lambda attr, value: value in attr,
            }
            str_operator_rex = re.compile(r'''(?x)
                \s*(?P<key>ext|acodec|vcodec|container|protocol|format_id)
                \s*(?P<negation>!\s*)?(?P<op>%s)(?P<none_inclusive>\s*\?)?
                \s*(?P<value>[a-zA-Z0-9._-]+)
                \s*$
                ''' % '|'.join(map(re.escape, STR_OPERATORS.keys())))
            m = str_operator_rex.search(filter_spec)
            if m:
                comparison_value = m.group('value')
                str_op = STR_OPERATORS[m.group('op')]
                if m.group('negation'):
                    op = lambda attr, value: not str_op
                else:
                    op = str_op

        if not m:
            raise ValueError('Invalid filter specification %r' % filter_spec)

        def _filter(f):
            actual_value = f.get(m.group('key'))
            if actual_value is None:
                return m.group('none_inclusive')
            return op(actual_value, comparison_value)
        return _filter
        stream = io.BytesIO(format_spec.encode('utf-8'))
        try:
            tokens = list(_remove_unused_ops(compat_tokenize_tokenize(stream.readline)))
        except tokenize.TokenError:
            raise syntax_error('Missing closing/opening brackets or parenthesis', (0, len(format_spec)))

        class TokenIterator(object):
            def __init__(self, tokens):
                self.tokens = tokens
                self.counter = 0

            def __iter__(self):
                return self

            def __next__(self):
                if self.counter >= len(self.tokens):
                    raise StopIteration()
                value = self.tokens[self.counter]
                self.counter += 1
                return value

            next = __next__

            def restore_last_token(self):
                self.counter -= 1

        parsed_selector = _parse_format_selection(iter(TokenIterator(tokens)))
        return _build_selector_function(parsed_selector)

    def _calc_headers(self, info_dict):
        res = std_headers.copy()

        add_headers = info_dict.get('http_headers')
        if add_headers:
            res.update(add_headers)

        cookies = self._calc_cookies(info_dict)
        if cookies:
            res['Cookie'] = cookies

        if 'X-Forwarded-For' not in res:
            x_forwarded_for_ip = info_dict.get('__x_forwarded_for_ip')
            if x_forwarded_for_ip:
                res['X-Forwarded-For'] = x_forwarded_for_ip

        return res

    def _calc_cookies(self, info_dict):
        pr = sanitized_Request(info_dict['url'])
        self.cookiejar.add_cookie_header(pr)
        return pr.get_header('Cookie')



    def download(self, url_list):
        print(url_list)
        """Download a given list of URLs."""
        outtmpl = self.params.get('outtmpl', DEFAULT_OUTTMPL)
        if (len(url_list) > 1 and
                outtmpl != '-' and
                '%' not in outtmpl and
                self.params.get('max_downloads') != 1):
            raise SameFileError(outtmpl)

        for url in url_list:
            try:
                # It also downloads the videos
                res = self.extract_info(
                    url, force_generic_extractor=self.params.get('force_generic_extractor', False))
            except UnavailableVideoError:
                self.report_error('unable to download video')
            except MaxDownloadsReached:
                self.to_screen('[info] Maximum number of downloaded files reached.')
                raise
            else:
                if self.params.get('dump_single_json', False):
                    self.to_stdout(json.dumps(res))

        return self._download_retcode

    def _make_archive_id(self, info_dict):
        # Future-proof against any change in case
        # and backwards compatibility with prior versions
        extractor = info_dict.get('extractor_key')
        if extractor is None:
            if 'id' in info_dict:
                extractor = info_dict.get('ie_key')  # key in a playlist
        if extractor is None:
            return None  # Incomplete video information
        return extractor.lower() + ' ' + info_dict['id']

    def _format_note(self, fdict):
        res = ''
        if fdict.get('ext') in ['f4f', 'f4m']:
            res += '(unsupported) '
        if fdict.get('language'):
            if res:
                res += ' '
            res += '[%s] ' % fdict['language']
        if fdict.get('format_note') is not None:
            res += fdict['format_note'] + ' '
        if fdict.get('tbr') is not None:
            res += '%4dk ' % fdict['tbr']
        if fdict.get('container') is not None:
            if res:
                res += ', '
            res += '%s container' % fdict['container']
        if (fdict.get('vcodec') is not None and
                fdict.get('vcodec') != 'none'):
            if res:
                res += ', '
            res += fdict['vcodec']
            if fdict.get('vbr') is not None:
                res += '@'
        elif fdict.get('vbr') is not None and fdict.get('abr') is not None:
            res += 'video@'
        if fdict.get('vbr') is not None:
            res += '%4dk' % fdict['vbr']
        if fdict.get('fps') is not None:
            if res:
                res += ', '
            res += '%sfps' % fdict['fps']
        if fdict.get('acodec') is not None:
            if res:
                res += ', '
            if fdict['acodec'] == 'none':
                res += 'video only'
            else:
                res += '%-5s' % fdict['acodec']
        elif fdict.get('abr') is not None:
            if res:
                res += ', '
            res += 'audio'
        if fdict.get('abr') is not None:
            res += '@%3dk' % fdict['abr']
        if fdict.get('asr') is not None:
            res += ' (%5dHz)' % fdict['asr']
        if fdict.get('filesize') is not None:
            if res:
                res += ', '
            res += format_bytes(fdict['filesize'])
        elif fdict.get('filesize_approx') is not None:
            if res:
                res += ', '
            res += '~' + format_bytes(fdict['filesize_approx'])
        return res
    def urlopen(self, req):
        """ Start an HTTP download """
        if isinstance(req, compat_basestring):
            req = sanitized_Request(req)
        return self._opener.open(req, timeout=self._socket_timeout)

    def print_debug_header(self):
        if not self.params.get('verbose'):
            return
        if type('') is not compat_str:
            # Python 2.6 on SLES11 SP1 (https://github.com/rg3/youtube-dl/issues/3326)
            self.report_warning(
                'Your Python is broken! Update to a newer and supported version')

        stdout_encoding = getattr(
            sys.stdout, 'encoding', 'missing (%s)' % type(sys.stdout).__name__)
        encoding_str = (
            '[debug] Encodings: locale %s, fs %s, out %s, pref %s\n' % (
                locale.getpreferredencoding(),
                sys.getfilesystemencoding(),
                stdout_encoding,
                self.get_encoding()))
        write_string(encoding_str, encoding=None)

        self._write_string('[debug] youtube-dl version ' + __version__ + '\n')
        if _LAZY_LOADER:
            self._write_string('[debug] Lazy loading extractors enabled' + '\n')
        try:
            sp = subprocess.Popen(
                ['git', 'rev-parse', '--short', 'HEAD'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__)))
            out, err = sp.communicate()
            out = out.decode().strip()
            if re.match('[0-9a-f]+', out):
                self._write_string('[debug] Git HEAD: ' + out + '\n')
        except Exception:
            try:
                sys.exc_clear()
            except Exception:
                pass

        def python_implementation():
            impl_name = platform.python_implementation()
            if impl_name == 'PyPy' and hasattr(sys, 'pypy_version_info'):
                return impl_name + ' version %d.%d.%d' % sys.pypy_version_info[:3]
            return impl_name

        self._write_string('[debug] Python version %s (%s) - %s\n' % (
            platform.python_version(), python_implementation(),
            platform_name()))

        proxy_map = {}
        for handler in self._opener.handlers:
            if hasattr(handler, 'proxies'):
                proxy_map.update(handler.proxies)
        self._write_string('[debug] Proxy map: ' + compat_str(proxy_map) + '\n')

        if self.params.get('call_home', False):
            ipaddr = self.urlopen('https://yt-dl.org/ip').read().decode('utf-8')
            self._write_string('[debug] Public IP address: %s\n' % ipaddr)
            latest_version = self.urlopen(
                'https://yt-dl.org/latest/version').read().decode('utf-8')
            if version_tuple(latest_version) > version_tuple(__version__):
                self.report_warning(
                    'You are using an outdated version (newest version: %s)! '
                    'See https://yt-dl.org/update if you need help updating.' %
                    latest_version)

    def _setup_opener(self):
        timeout_val = self.params.get('socket_timeout')
        self._socket_timeout = 600 if timeout_val is None else float(timeout_val)

        opts_cookiefile = self.params.get('cookiefile')
        opts_proxy = self.params.get('proxy')

        if opts_cookiefile is None:
            self.cookiejar = compat_cookiejar.CookieJar()
        else:
            opts_cookiefile = expand_path(opts_cookiefile)
            self.cookiejar = YoutubeDLCookieJar(opts_cookiefile)
            if os.access(opts_cookiefile, os.R_OK):
                self.cookiejar.load(ignore_discard=True, ignore_expires=True)

        cookie_processor = YoutubeDLCookieProcessor(self.cookiejar)
        if opts_proxy is not None:
            if opts_proxy == '':
                proxies = {}
            else:
                proxies = {'http': opts_proxy, 'https': opts_proxy}
        else:
            proxies = compat_urllib_request.getproxies()
            # Set HTTPS proxy to HTTP one if given (https://github.com/rg3/youtube-dl/issues/805)
            if 'http' in proxies and 'https' not in proxies:
                proxies['https'] = proxies['http']
        proxy_handler = PerRequestProxyHandler(proxies)

        debuglevel = 1 if self.params.get('debug_printtraffic') else 0
        https_handler = make_HTTPS_handler(self.params, debuglevel=debuglevel)
        ydlh = YoutubeDLHandler(self.params, debuglevel=debuglevel)
        data_handler = compat_urllib_request_DataHandler()
        file_handler = compat_urllib_request.FileHandler()
        def file_open(*args, **kwargs):
            raise compat_urllib_error.URLError('file:// scheme is explicitly disabled in youtube-dl for security reasons')
        file_handler.file_open = file_open
        opener = compat_urllib_request.build_opener(
            proxy_handler, https_handler, cookie_processor, ydlh, data_handler, file_handler)
        opener.addheaders = []
        self._opener = opener


