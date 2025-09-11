# e2i_api/apps/ingestion/migrations/0002_add_template_models.py

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_by', models.UUIDField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')], default='draft', max_length=16)),
                ('version', models.IntegerField(default=1)),
                ('target_table', models.CharField(default='applicants', max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_from_upload', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_templates', to='ingestion.upload')),
            ],
            options={
                'db_table': 'data_templates',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UploadExtension',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mapping_completed', models.BooleanField(default=False)),
                ('mapping_validated', models.BooleanField(default=False)),
                ('source_headers', models.JSONField(blank=True, default=list)),
                ('sample_data', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('selected_template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploads', to='ingestion.datatemplate')),
                ('upload', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='template_info', to='ingestion.upload')),
            ],
            options={
                'db_table': 'upload_template_info',
            },
        ),
        migrations.CreateModel(
            name='TemplateColumn',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128)),
                ('display_name', models.CharField(max_length=128)),
                ('data_type', models.CharField(choices=[('string', 'String'), ('integer', 'Integer'), ('float', 'Float'), ('datetime', 'DateTime'), ('date', 'Date'), ('boolean', 'Boolean')], default='string', max_length=16)),
                ('is_required', models.BooleanField(default=False)),
                ('max_length', models.IntegerField(blank=True, null=True)),
                ('min_value', models.FloatField(blank=True, null=True)),
                ('max_value', models.FloatField(blank=True, null=True)),
                ('regex_pattern', models.CharField(blank=True, max_length=512, null=True)),
                ('processing_type', models.CharField(choices=[('none', 'No Processing'), ('tokenize', 'Tokenize (PII)'), ('hash', 'Hash'), ('encrypt', 'Encrypt'), ('normalize', 'Normalize')], default='none', max_length=16)),
                ('processing_config', models.JSONField(blank=True, default=dict)),
                ('order', models.IntegerField(default=0)),
                ('merged_from_columns', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='columns', to='ingestion.datatemplate')),
            ],
            options={
                'db_table': 'template_columns',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ColumnMapping',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('source_column', models.CharField(max_length=128)),
                ('transform_function', models.CharField(blank=True, max_length=64, null=True)),
                ('transform_params', models.JSONField(blank=True, default=dict)),
                ('is_valid', models.BooleanField(default=True)),
                ('validation_errors', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('target_column', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_mappings', to='ingestion.templatecolumn')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='upload_mappings', to='ingestion.datatemplate')),
                ('upload', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='column_mappings', to='ingestion.upload')),
            ],
            options={
                'db_table': 'column_mappings',
            },
        ),
        migrations.AddIndex(
            model_name='datatemplate',
            index=models.Index(fields=['created_by'], name='idx_templates_creator'),
        ),
        migrations.AddIndex(
            model_name='datatemplate',
            index=models.Index(fields=['status'], name='idx_templates_status'),
        ),
        migrations.AddIndex(
            model_name='datatemplate',
            index=models.Index(fields=['target_table'], name='idx_templates_table'),
        ),
        migrations.AlterUniqueTogether(
            name='templatecolumn',
            unique_together={('template', 'name')},
        ),
        migrations.AddIndex(
            model_name='templatecolumn',
            index=models.Index(fields=['template', 'order'], name='idx_template_cols_order'),
        ),
        migrations.AlterUniqueTogether(
            name='columnmapping',
            unique_together={('upload', 'source_column'), ('upload', 'target_column')},
        ),
        migrations.AddIndex(
            model_name='columnmapping',
            index=models.Index(fields=['upload'], name='idx_mappings_upload'),
        ),
        migrations.AddIndex(
            model_name='columnmapping',
            index=models.Index(fields=['template'], name='idx_mappings_template'),
        ),
        
        # Add new upload status for mapped files
        migrations.RunSQL(
            "ALTER TABLE uploads ALTER COLUMN status TYPE VARCHAR(16)",
            reverse_sql="ALTER TABLE uploads ALTER COLUMN status TYPE VARCHAR(16)"
        ),
    ]