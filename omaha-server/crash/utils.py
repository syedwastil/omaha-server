# coding: utf8

"""
This software is licensed under the Apache 2 license, quoted below.

Copyright 2014 Crystalnix Limited

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy of
the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""

from builtins import str

import os
import re
import subprocess

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError

from crash.settings import MINIDUMP_STACKWALK_PATH, SYMBOLS_PATH
from crash.stacktrace_to_json import pipe_dump_to_json_dump
from crash.senders import get_sender
from omaha.models import Version
from sparkle.models import SparkleVersion


# This gets either a SentrySender or an ELKSender depending on config.
# crash_sender = get_sender()


class FileNotFoundError(Exception):
    pass


def get_stacktrace(crashdump_path):
    if not os.path.isfile(crashdump_path):
        raise FileNotFoundError

    cmd = [MINIDUMP_STACKWALK_PATH, '-m', crashdump_path, SYMBOLS_PATH]
    try:
        result = subprocess.check_output(cmd, universal_newlines=True)
        return result
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to process minidump: {e}")


def add_signature_to_frame(frame):
    frame = frame.copy()
    if 'function' in frame:
        # Remove spaces before all stars, ampersands, and commas
        function = re.sub(' (?=[\*&,])', '', frame['function'])
        # Ensure a space after commas
        function = re.sub(',(?! )', ', ', function)
        frame['function'] = function
        signature = function
    elif 'abs_path' in frame and 'lineno' in frame:
        signature = '%s#%d' % (frame['abs_path'], frame['lineno'])
    elif 'filename' in frame and 'module_offset' in frame:
        signature = '%s@%s' % (frame['filename'], frame['module_offset'])
    else:
        signature = '@%s' % frame['offset']
    frame['signature'] = signature
    frame['short_signature'] = re.sub('\(.*\)', '', signature)
    return frame


def parse_stacktrace(stacktrace):
    stacktrace_dict = pipe_dump_to_json_dump(str(stacktrace).splitlines())
    stacktrace_dict['crashing_thread']['frames'] = list(
        map(add_signature_to_frame,
            stacktrace_dict['crashing_thread']['frames']))
    return dict(stacktrace_dict)


def get_signature(stacktrace):
    try:
        frame = stacktrace['crashing_thread']['frames'][0]
        signature = frame['signature']
    except (KeyError, IndexError):
        signature = 'EMPTY: no frame data available'
    return signature


def get_os(stacktrace):
    return stacktrace.get('system_info', {}).get('os', '') if stacktrace else ''


def send_stacktrace(crash):
    stacktrace = crash.stacktrace_json
    exception = {
        "values": [
            {
                "type": stacktrace.get('crash_info', {}).get('type', 'unknown exception'),
                "value": stacktrace.get('crash_info', {}).get('crash_address', '0x0'),
                "stacktrace": stacktrace['crashing_thread']
            }
        ]
    }

    sentry_data = {'sentry.interfaces.Exception': exception}

    if crash.userid:
        sentry_data['sentry.interfaces.User'] = dict(id=crash.userid)

    extra = dict(
        crash_admin_panel_url='http://{}{}'.format(
            settings.HOST_NAME,
            '/admin/crash/crash/%s/' % crash.pk),
        crashdump_url=crash.upload_file_minidump.url,
    )

    tags = {}
    if crash.meta:
        extra.update(crash.meta)
        ver = crash.meta.get('ver')
        if ver:
            tags['ver'] = ver
    if crash.channel:
        tags['channel'] = crash.channel
    if crash.archive:
        extra['archive_url'] = crash.archive.url

    tags.update(stacktrace.get('system_info', {}))

    if crash.appid:
        tags['appid'] = crash.appid

    #crash_sender.send(crash.signature, extra=extra, tags=tags, sentry_data=sentry_data, crash_obj=crash)


def parse_debug_meta_info(head, exception=Exception):
    head = head.decode()
    head_list = head.split(' ', 4)
    if head_list[0] != 'MODULE':
        raise exception("The file contains invalid data.")
    return dict(debug_id=head_list[-2],
                debug_file=head_list[-1])


def get_channel(build_number, os):
    try:
        if os == 'Mac OS X':      # We expect that sparkle supports only Mac platform
            version = SparkleVersion.objects.select_related('channel').get(short_version=build_number)
        else:                       # All other platforms will be related to Omaha
            version = Version.objects.select_related('channel').get(version=build_number)
    except (MultipleObjectsReturned, ObjectDoesNotExist, ValidationError, ValueError):
        return 'undefined'
    return version.channel.name
