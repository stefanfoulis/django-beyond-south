from django.db.migrations.executor import MigrationExecutor


def dependencies(app_label, name, get_migration, deps=None):
    if deps is None:
        deps = set()
    deps.add((app_label, name))
    migration = get_migration(app_label, name)
    for sub_app_label, sub_name in migration.dependencies:
        if sub_app_label != app_label:
            continue
        dependencies(sub_app_label, sub_name, get_migration, deps=deps)
    return deps


class FakingMigrationExecutor(MigrationExecutor):

    def detect_soft_applied(self, project_state, migration):
        """
        This version of detect_soft_applied will mark migrations as applied
        if a south->this mapping is found.
        """
        found_create_migration, after_state = super(FakingMigrationExecutor, self).detect_soft_applied(project_state, migration)
        if (migration.app_label, migration.name) in self.targets_to_fake:
            return True, after_state
        return found_create_migration, after_state

    def __init__(self, *args, **kwargs):
        targets_to_fake = kwargs.pop('targets_to_fake', set())
        self.targets_to_fake = set()
        super(FakingMigrationExecutor, self).__init__(*args, **kwargs)
        for target in targets_to_fake:
            self.targets_to_fake.update(dependencies(target[0], target[1], self.loader.get_migration))

