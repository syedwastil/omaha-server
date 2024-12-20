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


import os
import hashlib
import base64
import logging

from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_save, pre_delete
from django.utils.timezone import now as datetime_now

from omaha.managers import VersionManager
from omaha.fields import PercentField
# Comment out S3 import for later use
# from omaha_server.s3utils import public_read_storage

# Add default Django storage
from django.core.files.storage import FileSystemStorage

# Define default storage
default_storage = FileSystemStorage()

from django_extensions.db.fields import (
    CreationDateTimeField, ModificationDateTimeField,
)
from jsonfield import JSONField
from versionfield import VersionField
from furl import furl
from storages.backends.s3boto3 import S3Boto3Storage


__all__ = ['Application', 'Channel', 'Platform', 'Version',
           'Action', 'EVENT_DICT_CHOICES', 'EVENT_CHOICES',
           'Data', 'AppRequest', 'Request', 'PartialUpdate',
           'BaseModel', 'version_upload_to', 'NAME_DATA_DICT_CHOICES']


class BaseModel(models.Model):
    created = CreationDateTimeField('created')
    modified = ModificationDateTimeField('modified')

    class Meta:
        abstract = True


class Application(BaseModel):
    id = models.CharField(max_length=38, primary_key=True)
    name = models.CharField(verbose_name='App', max_length=30, unique=True)

    class Meta:
        db_table = 'applications'
        ordering = ['id']

    def __str__(self):
        return self.name



class Platform(BaseModel):
    name = models.CharField(verbose_name='Platform', max_length=10, unique=True, db_index=True)
    verbose_name = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'platforms'

    def __str__(self):
        return self.name


class Channel(BaseModel):
    name = models.CharField(verbose_name='Channel', max_length=10, unique=True, db_index=True)

    class Meta:
        db_table = 'channels'

    def __str__(self):
        return self.name


def version_upload_to(obj, filename):
    return os.path.join('build', obj.app.name, obj.channel.name,
                        obj.platform.name, str(obj.version), filename)


def _version_upload_to(*args, **kwargs):
    return version_upload_to(*args, **kwargs)


class Version(BaseModel):
    is_enabled = models.BooleanField(default=True)
    is_critical = models.BooleanField(default=False)
    app = models.ForeignKey(Application, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, db_index=True, on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, db_index=True, on_delete=models.CASCADE)
    version = VersionField(help_text='Format: 255.255.65535.65535', number_bits=(8, 8, 16, 16), db_index=True)
    release_notes = models.TextField(blank=True, null=True)
    # Modified file field to use default storage instead of S3
    file = models.FileField(
        upload_to=_version_upload_to, 
        null=True,
        storage=S3Boto3Storage(),  
        blank=True
    )
    file_hash = models.CharField(verbose_name='Hash', max_length=140,
                                null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)

    objects = VersionManager()

    class Meta:
        db_table = 'versions'
        unique_together = (
            ('app', 'platform', 'channel', 'version'),
        )
        indexes = [
            models.Index(fields=['app', 'platform', 'channel', 'version'])
        ]
        ordering = ['id']

    def __str__(self):
        return "{app} {version}".format(app=self.app, version=self.version)

    @property
    def file_absolute_url(self):
        url = furl(self.file.url)
        if not url.scheme:
            url = '%s%s' % (settings.OMAHA_URL_PREFIX, url)
        return str(url)

    @property
    def file_package_name(self):
        url = furl(self.file_absolute_url)
        return os.path.basename(url.pathstr)

    @property
    def file_url(self):
        url = furl(self.file_absolute_url)
        if url.port and url.port != 80:
            return '%s://%s:%d%s/' % (url.scheme, url.host, url.port, os.path.dirname(url.pathstr))
        else:
            return '%s://%s%s/' % (url.scheme, url.host, os.path.dirname(url.pathstr))

    @property
    def size(self):
        return self.file_size

    def get_file_url(self):
        """Generate a temporary URL for file download"""
        if self.file:
            try:
                s3_client = self.file.storage.connection
                return s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.file.storage.bucket_name,
                        'Key': self.file.name
                    },
                    ExpiresIn=3600  # URL valid for 1 hour
                )
            except Exception as e:
                logger.error(f"Error generating presigned URL: {str(e)}")
                return None
        return None


EVENT_DICT_CHOICES = dict(
    preinstall=0,
    install=1,
    postinstall=2,
    update=3,
)

EVENT_CHOICES = list(zip(list(EVENT_DICT_CHOICES.values()), list(EVENT_DICT_CHOICES.keys())))


class Action(BaseModel):
    version = models.ForeignKey(Version, db_index=True, related_name='actions', on_delete=models.CASCADE)
    event = models.PositiveSmallIntegerField(
        choices=EVENT_CHOICES,
        help_text='Contains a fixed string denoting when this action should be run.')
    run = models.CharField(
        max_length=255, null=True, blank=True,
        help_text='The name of an installer binary to run.')
    arguments = models.CharField(
        max_length=255, null=True, blank=True,
        help_text='Arguments to be passed to that installer binary.')
    successurl = models.URLField(
        null=True, blank=True,
        help_text="A URL to be opened using the system's "
                  "default web browser on a successful install.")
    terminateallbrowsers = models.BooleanField(
        default=False,
        help_text='If "true", close all browser windows before starting the installer binary.')
    onsuccess = models.CharField(
        null=True, max_length=255, blank=True,
        help_text='Contains a fixed string denoting some action to take '
                  'in response to a successful install')
    other = JSONField(verbose_name='Other attributes', help_text='JSON format', null=True, blank=True,)

    class Meta:
        db_table = 'actions'
        ordering = ['id']

    def get_attributes(self):
        exclude_fields = ('id', 'version', 'event', 'other', 'created',
                          'modified', 'terminateallbrowsers')
        attrs = dict([(field.name, str(getattr(self, field.name)))
                      for field in self._meta.fields
                      if field.name not in exclude_fields
                      and getattr(self, field.name)])
        if self.terminateallbrowsers:
            attrs['terminateallbrowsers'] = 'true'
        attrs.update(self.other or {})
        return attrs


ACTIVE_USERS_DICT_CHOICES = dict(
    all=0,
    week=1,
    month=2,
)

ACTIVE_USERS_CHOICES = list(zip(list(ACTIVE_USERS_DICT_CHOICES.values()), list(ACTIVE_USERS_DICT_CHOICES.keys())))


class PartialUpdate(models.Model):
    is_enabled = models.BooleanField(default=True, db_index=True)
    version = models.OneToOneField(Version, db_index=True, on_delete=models.CASCADE)
    percent = PercentField()
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    exclude_new_users = models.BooleanField(default=True)
    active_users = models.PositiveSmallIntegerField(
        help_text='Active users in the past ...',
        choices=ACTIVE_USERS_CHOICES, default=1)


NAME_DATA_DICT_CHOICES = dict(
    install=0,
    untrusted=1,
)

NAME_DATA_CHOICES = list(zip(list(NAME_DATA_DICT_CHOICES.values()), list(NAME_DATA_DICT_CHOICES.keys())))


class Data(BaseModel):
    app = models.ForeignKey(Application, db_index=True, on_delete=models.CASCADE)
    name = models.PositiveSmallIntegerField(choices=NAME_DATA_CHOICES)
    index = models.CharField(max_length=255, null=True, blank=True)
    value = models.TextField(null=True, blank=True)


class Os(models.Model):
    platform = models.CharField(max_length=10, null=True, blank=True)
    version = models.CharField(max_length=16, null=True, blank=True)
    sp = models.CharField(max_length=40, null=True, blank=True)
    arch = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        unique_together = (
            ('platform', 'version', 'sp', 'arch'),
        )


class Hw(models.Model):
    sse = models.PositiveIntegerField(null=True, blank=True)
    sse2 = models.PositiveIntegerField(null=True, blank=True)
    sse3 = models.PositiveIntegerField(null=True, blank=True)
    ssse3 = models.PositiveIntegerField(null=True, blank=True)
    sse41 = models.PositiveIntegerField(null=True, blank=True)
    sse42 = models.PositiveIntegerField(null=True, blank=True)
    avx = models.PositiveIntegerField(null=True, blank=True)
    physmemory = models.PositiveIntegerField(null=True, blank=True)


class Request(models.Model):
    os = models.ForeignKey(Os, null=True, blank=True, on_delete=models.CASCADE)
    hw = models.ForeignKey(Hw, null=True, blank=True, on_delete=models.CASCADE)
    version = VersionField(help_text='Format: 255.255.65535.65535', number_bits=(8, 8, 16, 16))
    ismachine = models.PositiveSmallIntegerField(null=True, blank=True)
    sessionid = models.CharField(max_length=40, null=True, blank=True)
    userid = models.CharField(max_length=40, null=True, blank=True)
    installsource = models.CharField(max_length=40, null=True, blank=True)
    originurl = models.URLField(null=True, blank=True)
    testsource = models.CharField(max_length=40, null=True, blank=True)
    updaterchannel = models.CharField(max_length=10, null=True, blank=True)
    created = models.DateTimeField(db_index=True, default=datetime_now, editable=False, blank=True)
    ip = models.GenericIPAddressField(blank=True, null=True, protocol='IPv4')


class Event(models.Model):
    eventtype = models.PositiveSmallIntegerField(db_index=True)
    eventresult = models.PositiveSmallIntegerField()
    errorcode = models.IntegerField(null=True, blank=True)
    extracode1 = models.IntegerField(null=True, blank=True)
    download_time_ms = models.PositiveIntegerField(null=True, blank=True)
    downloaded = models.PositiveIntegerField(null=True, blank=True)
    total = models.PositiveIntegerField(null=True, blank=True)
    update_check_time_ms = models.PositiveIntegerField(null=True, blank=True)
    install_time_ms = models.PositiveIntegerField(null=True, blank=True)
    source_url_index = models.URLField(null=True, blank=True)
    state_cancelled = models.PositiveIntegerField(null=True, blank=True)
    time_since_update_available_ms = models.PositiveIntegerField(null=True, blank=True)
    time_since_download_start_ms = models.PositiveIntegerField(null=True, blank=True)
    nextversion = models.CharField(max_length=40, null=True, blank=True)
    previousversion = models.CharField(max_length=40, null=True, blank=True)

    @property
    def is_error(self):
        if self.eventtype in (100, 102, 103):
            return True
        elif self.eventresult not in (1, 2, 3):
            return True
        elif self.errorcode != 0:
            return True
        return False


class AppRequest(models.Model):
    request = models.ForeignKey(Request, db_index=True, on_delete=models.CASCADE)
    appid = models.CharField(max_length=38, db_index=True)
    version = VersionField(help_text='Format: 255.255.65535.65535',
                           number_bits=(8, 8, 16, 16), default=0, null=True, blank=True)
    nextversion = VersionField(help_text='Format: 255.255.65535.65535',
                               number_bits=(8, 8, 16, 16), default=0, null=True, blank=True)
    lang = models.CharField(max_length=40, null=True, blank=True)
    tag = models.CharField(max_length=40, null=True, blank=True)
    installage = models.SmallIntegerField(null=True, blank=True)
    events = models.ManyToManyField(Event)


@receiver(pre_save, sender=Version)
def pre_version_save(sender, instance, *args, **kwargs):
    if instance.pk:
        old = sender.objects.get(pk=instance.pk)
        if old.file == instance.file:
            return
        else:
            try:
                old.file.delete(save=False)
            except:
                pass
            finally:
                old.file_size = 0
    sha1 = hashlib.sha1()
    for chunk in instance.file.chunks():
        sha1.update(chunk)
    instance.file.seek(0)
    instance.file_hash = base64.b64encode(sha1.digest()).decode()


@receiver(pre_delete, sender=Version)
def pre_version_delete(sender, instance, **kwargs):
    storage, name = instance.file.storage, instance.file.name
    if name:
        storage.delete(name)

