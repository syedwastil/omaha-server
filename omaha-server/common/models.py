from django.db import models
from django.contrib.auth.models import User

class RequestLog(models.Model):
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
        # Add other HTTP methods as needed
    ]

    path = models.CharField(max_length=2048)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    query_params = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    headers = models.TextField(blank=True, null=True)
    status_code = models.IntegerField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code}"
