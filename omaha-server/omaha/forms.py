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

from collections import OrderedDict

from django.forms import widgets, ValidationError, ModelForm, Form, IntegerField, ChoiceField, Select

from django_ace import AceWidget
from omaha.widgets import CustomTinyMCE
from celery import signature

from omaha.models import Application, Version, Action, Data


__all__ = ['ApplicationAdminForm', 'VersionAdminForm', 'ActionAdminForm', 'DataAdminForm']


class ApplicationAdminForm(ModelForm):
    def clean_id(self):
        return self.cleaned_data["id"].upper()

    class Meta:
        model = Application
        exclude = []


class DataAdminForm(ModelForm):
    class Meta:
        model = Data
        exclude = []
        widgets = {
            'value': AceWidget(mode='json', theme='monokai', width='600px', height='300px'),
        }


class VersionAdminForm(ModelForm):
    class Meta:
        model = Version
        exclude = []
        widgets = {
            'app': Select,
            'release_notes': CustomTinyMCE(),
            'file_size': widgets.TextInput(attrs=dict(disabled='disabled')),
            'version': widgets.TextInput(),
        }

    def clean_file_size(self):
        if 'file' not in self.cleaned_data:
            raise ValidationError('')
        _file = self.cleaned_data["file"]
        return _file.size


class ActionAdminForm(ModelForm):
    ONSUCCESS_CHOICES = (
        ('default', 'default'),
        ('exitsilently', 'exitsilently'),
        ('exitsilentlyonlaunchcmd', 'exitsilentlyonlaunchcmd')
    )
    onsuccess = ChoiceField(choices=ONSUCCESS_CHOICES)

    class Meta:
        model = Action
        exclude = []


class ManualCleanupForm(Form):
    limit_days = IntegerField(min_value=1, required=False, label='Maximum age (days)',
                                    help_text=' - remove objects older than X days')
    limit_size = IntegerField(min_value=1, required=False, label='Purge used space (Gb)',
                                    help_text=" - remove old objects until total size won't reach X GB")

    def cleanup(self):
        model = self.initial['type'].split('__')
        task_kwargs = self.get_task_kwargs()
        signature("tasks.deferred_manual_cleanup", args=(model,), kwargs=task_kwargs).apply_async(queue='limitation')

    def get_task_kwargs(self):
        task_kwargs = dict(
            limit_size=self.cleaned_data['limit_size'],
            limit_days=self.cleaned_data['limit_days'],
        )
        return task_kwargs


class CrashManualCleanupForm(ManualCleanupForm):
    limit_duplicated = IntegerField(min_value=1, required=False, label='Maximum amount of duplicates',
                                          help_text=" - remove old duplicate crashes until their number won't equal X ")

    def __init__(self, *args, **kwargs):
        super(CrashManualCleanupForm, self).__init__(*args, **kwargs)
        fields = OrderedDict()
        for key in ("limit_duplicated", "limit_days", "limit_size"):
            fields[key] = self.fields.pop(key)
        for key, value in list(self.fields.items()):
            fields[key] = value
        self.fields = fields

    def get_task_kwargs(self):
        task_kwargs = super(CrashManualCleanupForm, self).get_task_kwargs()
        task_kwargs.update(dict(limit_duplicated=self.cleaned_data['limit_duplicated']))
        return task_kwargs
