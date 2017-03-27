# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.conf import settings


class SouthMigration(models.Model):
    app_name = models.CharField(max_length=255)
    migration = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'south_migrationhistory'
        ordering = (
            'app_name',
            'migration',
        )

    @property
    def is_installed(self):
        return self.app_name in settings.INSTALLED_APPS


# class DjangoMigration(models.Model):
#     app_name = models.CharField(max_length=255)
#     migration = models.CharField(max_length=255)
#     applied = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'south_migrationhistory'
#         ordering = (
#             'app_name',
#             'migration',
#         )
