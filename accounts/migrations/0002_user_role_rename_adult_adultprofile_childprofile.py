# Generated by Django 4.2.17 on 2025-03-09 11:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('ADMIN', 'Admin'), ('ADULT', 'Adult'), ('CHILD', 'Child')], default='ADMIN', max_length=10),
        ),
        migrations.RenameModel(
            old_name='Adult',
            new_name='AdultProfile',
        ),
        migrations.CreateModel(
            name='ChildProfile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('exercise_language', models.CharField(choices=[('en', 'English')], default='en', max_length=50)),
                ('exercise_level', models.CharField(choices=[('letters', 'Letters'), ('words', 'Words'), ('category', 'Category')], default='letters', max_length=50)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.adultprofile')),
            ],
        ),
    ]
