# Generated manually to ensure El Paso is available as an event place.

from django.db import migrations


def add_el_paso_place(apps, schema_editor):
    Places = apps.get_model("calendar_app", "Places")
    if not Places.objects.filter(name="El Paso").exists():
        Places.objects.create(name="El Paso")


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_app", "0014_alter_activity_telescope"),
    ]

    operations = [
        migrations.RunPython(add_el_paso_place, migrations.RunPython.noop),
    ]
