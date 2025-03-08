# Generated manually

from django.db import migrations, models
from decimal import Decimal

class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0002_paymentschedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentschedule',
            name='installment_number',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='paymentschedule',
            name='amount_paid',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.AddField(
            model_name='paymentschedule',
            name='penalty_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.AddField(
            model_name='paymentschedule',
            name='last_reminder_sent',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RenameField(
            model_name='paymentschedule',
            old_name='total_amount',
            new_name='amount',
        ),
    ]