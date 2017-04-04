# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
from pprint import pprint as pp
from django.utils.importlib import import_module
import yaml
from django.conf import settings
import django.db.utils

from ..models import SouthMigration, DjangoMigration


def _migrations_filenames(directory):
    return [
        filename
        for filename in os.listdir(directory)
        if (
            os.path.splitext(filename)[1] == '.py' and
            filename[:4].isdigit()
        )
    ]


def _detect_directory(app_directory, directories, samples):
    for directory in directories:
        migrations_dir = os.path.join(app_directory, directory)
        if not os.path.exists(migrations_dir):
            continue
        filenames = _migrations_filenames(migrations_dir)
        if not filenames:
            continue
        with open(os.path.join(migrations_dir, filenames[0]), mode='r') as migration_file:
            file_content = migration_file.read()
            if all([str(sample) in file_content for sample in samples]):
                return migrations_dir


def detect_south_directory(app_directory):
    return _detect_directory(
        app_directory=app_directory,
        directories=['south_migrations', 'migrations'],
        samples=['south', 'SchemaMigration']
    )


def detect_migrations_directory(app_directory):
    return _detect_directory(
        app_directory=app_directory,
        directories=['django_migrations', 'migrations'],
        samples=['from django.db import migrations']
    )


def discover_migrations_in_filesystem(directory_detector):
    apps_without_migrations = []
    all_migrations = {}

    for app_name in settings.INSTALLED_APPS:
        app = import_module(app_name)
        app_dir = os.path.dirname(app.__file__)
        migrations_dir = directory_detector(app_dir)
        if not migrations_dir:
            apps_without_migrations.append(app_name)
            continue
        migrations = {
            os.path.splitext(filename)[0]: None
            for filename in os.listdir(migrations_dir)
            if (
                os.path.splitext(filename)[1] == '.py' and
                filename[:4].isdigit()
            )
        }
        all_migrations[app_name] = migrations

    # print("=== APPS without migrations")
    # for app in apps_without_migrations:
    #     print(app)
    return all_migrations


def discover_migrations_in_db(only_installed=True):
    all_migrations = {}
    try:
        for migration in SouthMigration.objects.all():
            if only_installed and not migration.is_installed:
                continue
            migrations = all_migrations.setdefault(migration.app_name, {})
            migrations[migration.migration] = None
    except django.db.utils.ProgrammingError:
        pass
    finally:
        return all_migrations


def discover_south_migrations():
    all_migrations = {}

    fs = discover_migrations_in_filesystem(
        directory_detector=detect_south_directory
    )
    for app_name, migrations in fs.items():
        new_migrations = all_migrations.setdefault(app_name, {})
        for migration in migrations:
            new_migrations[migration] = None

    db = discover_migrations_in_db(only_installed=False)
    for app_name, migrations in db.items():
        new_migrations = all_migrations.setdefault(app_name, {})
        for migration in migrations:
            new_migrations[migration] = None
    return all_migrations


def discover_django_migrations():
    return discover_migrations_in_filesystem(directory_detector=detect_migrations_directory)


def load_mapping_from_files(basedir='south2migrations'):
    filenames = set([
        filename
        for filename in os.listdir(basedir)
        if os.path.splitext(filename)[1] == '.yml'
    ])
    all_migrations = {}
    for filename in filenames:
        with open(os.path.join(basedir, filename), 'r') as ymlfile:
            data = yaml.safe_load(ymlfile)
        for app_name, migrations in data.items():
            app_migrations = all_migrations.setdefault(app_name, {})
            for south_migration, django_migration in migrations.items():
                app_migrations[south_migration] = django_migration
    return all_migrations


def write_migration_yaml(app_migrations, basedir='south2migrations'):
    try:
        os.makedirs(basedir)
    except OSError:
        pass
    for app_name, migrations in app_migrations.items():
        filename = os.path.join(basedir, '{}.yml'.format(app_name))
        with open(filename, 'w+') as yamlfile:
            yaml.safe_dump(
                data={app_name: migrations},
                # data={'south-to-migrations': dict(migrations_dict)},
                # data=dict(migrations_dict),
                stream=yamlfile,
                default_flow_style=False,
            )


def get_migration_mappings_needed(only_installed=True, app_names=None):
    """
    Return the migration mappings needed to switch the current database from
    South to Django Migrations.
    """
    latest_migrations = {}
    if app_names is None:
        app_names = (
            SouthMigration.objects.all()
            .only('app_name')
            .distinct('app_name')
            .values_list('app_name', flat=True)
        )
    for app_name in app_names:
        latest_migration = (
            SouthMigration.objects
            .filter(app_name=app_name)
            .order_by('-migration')
            .first()
        )
        if only_installed and not latest_migration.is_installed:
            continue
        latest_migrations[app_name] = latest_migration.migration
    return latest_migrations


def get_migration_for_south_migration(app_name, south_migration, mapping=None):
    mapping = mapping or load_mapping_from_files()
    return mapping.get(app_name, {}).get(south_migration, None)


def latest_django_migrations(only_installed=True, app_names=None):
    latest_migrations = {}
    try:
        if app_names is None:
            app_names = (
                DjangoMigration.objects.all()
                .only('app')
                .distinct('app')
                .values_list('app', flat=True)
            )
        for app_name in app_names:
            latest_migration = (
                DjangoMigration.objects
                .filter(app=app_name)
                .order_by('-name')
                .first()
            )
            if only_installed and not latest_migration.is_installed:
                continue
            latest_migrations[app_name] = latest_migration.name
    except django.db.utils.ProgrammingError:
        pass
    finally:
        return latest_migrations


def migration_status(mapping=None):
    migrations_needed = get_migration_mappings_needed()
    mapping = mapping or load_mapping_from_files()

    already_migrated = latest_django_migrations()
    to_migrate = {}
    missing_mapping = {}
    for app_name, south_name in migrations_needed.items():
        if app_name in already_migrated:
            continue
        name = get_migration_for_south_migration(app_name, south_name, mapping=mapping)
        if name:
            to_migrate[app_name] = (south_name, name)
        else:
            missing_mapping[app_name] = south_name
    return already_migrated, to_migrate, missing_mapping


def discover_it():
    all_migrations = discover_south_migrations()
    defined_migrations = load_mapping_from_files()
    for app_name, migrations in defined_migrations.items():
        for south_migration, django_migration in migrations.items():
            app_migrations = all_migrations.setdefault(app_name, {})
            app_migrations[south_migration] = django_migration
    needed = get_migration_mappings_needed()
    pp(needed)
    # pp(all_migrations)
    write_migration_yaml(all_migrations)


def init_django_migrations():
    # TODO: Check we're in Django 1.7+

    # TODO: find out which apps need migrating

    needed_migrations = get_migration_mappings_needed()

    south_state = discover_migrations_in_db(only_installed=True)

    # Lookup applied South migrations and pick the correct Django migration.
    defined_migrations = load_mapping_from_files()
    migrate_mapping = {}
    for app_name, migrations in south_state.items():

        new_mapping = migrate_mapping.setdefault(app_name, {})

    # Report on missing mappings

    # --fake the django migrations

    # Run migrate with --fake-initial to pick up all the apps that did not have
    # migrations before.

    return
