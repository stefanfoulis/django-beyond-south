# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
from collections import OrderedDict
from pprint import pprint as pp
from django.utils.importlib import import_module
import ruamel.yaml
import yaml
from django.conf import settings


def detect_south_directory(app_directory):
    # TODO: make this a bit smarter by probing the files inside the common
    #       directories migrations, south_migrations and django_migrations to
    #       find out which really is the correct one.
    return os.path.join(app_directory, 'south_migrations')


def detect_migrations_directory(app_directory):
    # TODO: make this a bit smarter by probing the files inside the common
    #       directories migrations, south_migrations and django_migrations to
    #       find out which really is the correct one.
    return os.path.join(app_directory, 'migrations')


def discover_migrations(directory_detector):
    apps_without_migrations = []
    all_migrations = {}

    for app_name in settings.INSTALLED_APPS:
        app = import_module(app_name)
        app_dir = os.path.dirname(app.__file__)
        migrations_dir = directory_detector(app_dir)
        if not os.path.exists(migrations_dir):
            apps_without_migrations.append(app_name)
            continue
        migrations = sorted([
            os.path.splitext(filename)[0]
            for filename in os.listdir(migrations_dir)
            if (
                os.path.splitext(filename)[1] == '.py' and
                filename[:4].isdigit()
            )
        ])
        pp(migrations)
        all_migrations[app_name] = migrations

    print("=== APPS without migrations")
    for app in apps_without_migrations:
        print(app)

    print("=== APPS with migrations")

    return all_migrations


def south():
    return discover_migrations(directory_detector=detect_south_directory)


def migrations():
    return discover_migrations(directory_detector=detect_migrations_directory)


def write_empty_migration_yaml(app_migrations, basedir='south2migrations'):
    try:
        os.makedirs(basedir)
    except OSError:
        pass
    for app_name, migrations in app_migrations.items():
        migrations_dict = OrderedDict([(name, None) for name in migrations])
        filename = os.path.join(basedir, '{}.yml'.format(app_name))
        with open(filename, 'w+') as yamlfile:
            yaml.safe_dump(
                data={app_name: dict(migrations_dict)},
                # data={'south-to-migrations': dict(migrations_dict)},
                # data=dict(migrations_dict),
                stream=yamlfile,
                default_flow_style=False,
            )


def doit():
    all_migrations = south()
    write_empty_migration_yaml(all_migrations)
