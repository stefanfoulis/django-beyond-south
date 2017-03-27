# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from . import models


class SouthMigrationAdmin(admin.ModelAdmin):
    list_display = (
        'app_name',
        'is_installed',
        'migration',
        'applied',
    )
    list_filter = (
        'applied',
        'app_name',
    )

    def is_installed(self, obj):
        return obj.is_installed
    is_installed.boolean = True
    is_installed.short_description = 'installed'


# class DjangoMigrationAdmin(admin.ModelAdmin):
#     pass

admin.site.register(models.SouthMigration, SouthMigrationAdmin)
