from django.db import models


class ExchangeRates(models.Model):
    pk = models.CompositePrimaryKey('bank_id', 'rate_date', 'currency_code', 'rate_type')
    bank = models.ForeignKey('Banks', models.DO_NOTHING)
    rate_date = models.DateField()
    currency_code = models.CharField(max_length=3)
    rate_type = models.TextField()
    rate = models.DecimalField(max_digits=14, decimal_places=4)
    loaded_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'exchange_rates'


class Banks(models.Model):
    bank_id = models.AutoField(primary_key=True)
    bank_name = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = 'banks'
