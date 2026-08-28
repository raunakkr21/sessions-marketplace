import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('marketplace_sessions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('session', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to='marketplace_sessions.session',
                )),
                ('user', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('status', models.CharField(
                    choices=[('active', 'Active'), ('cancelled', 'Cancelled')],
                    db_index=True,
                    default='active',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'bookings_booking',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='booking',
            constraint=models.UniqueConstraint(
                condition=models.Q(status='active'),
                fields=['user', 'session'],
                name='unique_active_booking_per_user_session',
            ),
        ),
    ]
