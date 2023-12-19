# Generated by Django 3.2.21 on 2023-10-25 15:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0063_provider_request_related_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='datacentersupportingdocument',
            name='archived',
            field=models.BooleanField(default=False, editable=False, help_text='If this is checked, this document will not show up in any queries. Should not editable via the admin interface by non-staff users.'),
        ),
        migrations.AddField(
            model_name='hostingprovidersupportingdocument',
            name='archived',
            field=models.BooleanField(default=False, editable=False, help_text='If this is checked, this document will not show up in any queries. Should not editable via the admin interface by non-staff users.'),
        ),
        migrations.AlterField(
            model_name='hostingproviderstats',
            name='hostingprovider',
            field=models.OneToOneField(db_column='id_hp', on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='accounts.hostingprovider'),
        ),
    ]