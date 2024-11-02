from django.shortcuts import render
import logging

from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse

from lxml.etree import XMLSyntaxError

from omaha.builder import build_response
from config.utils import get_client_ip
from omaha.models import Request

class UpdateView(View):
    http_method_names = ['post']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(UpdateView, self).dispatch(*args, **kwargs)

    def post(self, request):
        try:
            response = build_response(request.body, ip=get_client_ip(request))
        except XMLSyntaxError:
            logger.error('UpdateView', exc_info=True, extra=dict(request=request))
            msg = b"""<?xml version="1.0" encoding="utf-8"?>
                    <data>
                        <message>
                            Bad Request
                        </message>
                    </data>"""
            return HttpResponse(msg, status=400, content_type="text/html; charset=utf-8")
        return HttpResponse(response, content_type="text/xml; charset=utf-8")

