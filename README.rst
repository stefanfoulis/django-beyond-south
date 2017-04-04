Django Beyond South
===================

Warning: This is a prototype! Very experimental and messy. It will not
         "just work" (yet).

Helps switch from Django 1.6 and South to Django 1.7+ and native django migrations.
Automates the faking of all migrations to keep a consistent database by maintaining south to django migration mappings for well known apps.


TODO:

* proper addon setup that replaces the regular migrate
* make migrate command smart enough to be runnable as a replacement of the
  default one.
* major cleanup needed
* mapping file discovery (have some bundled but also load from a project
  specific location or from the installed apps).
