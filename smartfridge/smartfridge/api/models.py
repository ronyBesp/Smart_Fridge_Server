# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models as models
from django.contrib.auth.models import User, Group
from django.utils.dateformat import format
from datetime import datetime
import uuid
from jsonfield import JSONField

def upload_path_formatting(instance, filename):
        return '{0}/{1}'.format(instance.user_name, filename)

# Create your models here.
class FridgeContents(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Will upload to the default media path which is set to /uploads -> configured in settings
    img = models.ImageField(upload_to=upload_path_formatting, max_length=254)
    # Fields
    created = models.DateTimeField(auto_now_add=True, editable=False)
    last_updated = models.DateTimeField(auto_now=True, editable=False)
    user_name = models.CharField(max_length=255)
    # JSONFIELD PIP MODULE USED
    resultDict = JSONField(default={})
    shelfImgPaths = JSONField(default={})
    withinShelfImgPaths = JSONField(default={})
    previousCapList = models.TextField(null=True)
    capacity = models.TextField(null=True)
    

    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return u'%s' % self.user_name

