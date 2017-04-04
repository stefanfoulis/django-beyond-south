# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import partial

import djclick as click
from ...utils import discover as dicover_utils


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    '--include-all/--no-include-all',
    default=False,
    help='Whether to include migrations. Even those from apps that are '
         'currently not installed.',
)
def discover(include_all):
    """
    Discovers all South migrations in the database and on disk. Then writes them
    into a
    """
    dicover_utils.discover_it()


@cli.command()
def mappings():
    mapping = dicover_utils.load_mapping_from_files()
    already_migrated, to_migrate, missing_mapping = dicover_utils.migration_status(mapping=mapping)
    click.echo('Already migrated:')
    for app_name, migration in sorted(already_migrated.items()):
        click.echo(' [ {} ] {}'.format(app_name, migration))
    if not already_migrated:
        click.echo(' none')

    click.echo('Ready to migrate:')
    for app_name, (south_migration, django_migration) in sorted(to_migrate.items()):
        click.echo(' [ {} ] {}  ->  {}'.format(app_name, south_migration, django_migration))
    if not to_migrate:
        click.echo(' none')

    click.echo('Mapping to django migration missing:')
    for app_name, south_migration in sorted(missing_mapping.items()):
        click.echo(' [ {} ] {}'.format(app_name, south_migration))
    if not missing_mapping:
        click.echo(' none')


@cli.command()
def migrate():
    # TODO: check if we're in Django 1.7+
    click.echo('Going beyond South....')
    mapping = dicover_utils.load_mapping_from_files()
    already_migrated, to_migrate, missing_mapping = dicover_utils.migration_status(mapping=mapping)
    if not to_migrate:
        click.echo(' Nothing to do')

    # begin: adaption of django management command
    from django.apps import apps
    from django.db import connections
    from django.utils.module_loading import module_has_submodule
    from importlib import import_module
    from django.db.migrations.executor import MigrationExecutor
    from ...utils.executor import FakingMigrationExecutor

    targets = {}
    for app_name, (south_migration, django_migration) in sorted(to_migrate.items()):
        targets[app_name] = django_migration

    for app_config in apps.get_app_configs():
        if module_has_submodule(app_config.module, "management"):
            import_module('.management', app_config.name)

    connection = connections['default']
    connection.prepare_database()
    progress = partial(migration_progress_callback, echo=click.echo)
    executor = FakingMigrationExecutor(
        connection=connection,
        progress_callback=progress,
        targets_to_fake=targets.items(),
    )
    # executor.loader.check_consistent_history(connection)
    conflicts = executor.loader.detect_conflicts()
    if conflicts:
        name_str = "; ".join(
            "%s in %s" % (", ".join(names), app)
            for app, names in conflicts.items()
        )
        raise click.ClickException(
            "Conflicting migrations detected; multiple leaf nodes in the "
            "migration graph: (%s).\nTo fix them run "
            "'python manage.py makemigrations --merge'" % name_str
        )
    for app_name, django_migration in targets.items():
        if app_name not in executor.loader.migrated_apps:
            raise click.ClickException("App '%s' does not have migrations." % app_name)
    # for app_name in executor.loader.migrated_apps:
    #     # Add any other apps to the targeted migrations. Since we're
    #     if app_name in to_migrate.keys():
    #         # We already have a target for this app. No need to migrate.
    #         # print '{} already has a target'.format(app_name)
    #         continue
    #     elif app_name in already_migrated.keys():
    #         # This app has already been migrated. Don't touch it.
    #         # print '{} has already been migrated.'.format(app_name)
    #         continue
    #     # TODO: Avoid hardcoding 0001_initial
    #     # print 'Adding {}'.format(app_name)
    #     targets[app_name] = '0001_initial'
    plan = executor.migration_plan(targets.items())
    executor.migrate(targets.items(), plan, fake=False, fake_initial=True)

    # Now run a regular migration with fake_initial to get all the other apps
    # migrated.
    executor2 = MigrationExecutor(
        connection=connection,
        progress_callback=progress,
    )
    targets2 = executor.loader.graph.leaf_nodes()
    plan2 = executor2.migration_plan(targets2)
    executor.migrate(targets2, plan2, fake=False, fake_initial=True)

    # end

import time


def migration_progress_callback(action, migration=None, fake=False, echo=None, verbosity=5):
    if verbosity >= 1:
        compute_time = verbosity > 1
        start = time.time()
        if action == "apply_start":
            echo("  Applying %s..." % migration, nl=False)
        elif action == "apply_success":
            elapsed = " (%.3fs)" % (time.time() - start) if compute_time else ""
            if fake:
                echo(" FAKED" + elapsed)
            else:
                echo(" OK" + elapsed)
        elif action == "unapply_start":
            echo("  Unapplying %s..." % migration, nl=False)
        elif action == "unapply_success":
            elapsed = " (%.3fs)" % (time.time() - start) if compute_time else ""
            if fake:
                echo(" FAKED" + elapsed)
            else:
                echo(" OK" + elapsed)
        elif action == "render_start":
            echo("  Rendering model states...", nl=False)
        elif action == "render_success":
            elapsed = " (%.3fs)" % (time.time() - start) if compute_time else ""
            echo(" DONE" + elapsed)
