from django.db import models


class MyModel(models.Model):

    field_char = models.CharField(max_length=255)
    field_text = models.TextField()
    field_bool = models.BooleanField()
    field_int = models.IntegerField()
    field_datetime = models.DateTimeField()
    field_date = models.DateField()


class MyRelatedModel(models.Model):

    field_fk = models.ForeignKey(MyModel)
