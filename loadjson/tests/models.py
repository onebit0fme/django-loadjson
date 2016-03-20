from django.db import models
from django.utils import timezone


class MyRelatedModel(models.Model):

    name = models.CharField(max_length=255)
    key = models.IntegerField()

    def __str__(self):
        return str(self.key)


class MyModel(models.Model):

    char_field = models.CharField(max_length=255, default='')
    text_field = models.TextField(default='')
    bool_field = models.BooleanField(default=False)
    int_field = models.IntegerField(default=0)
    datetime_field = models.DateTimeField(default=timezone.now)
    date_field = models.DateField(default=timezone.now)
    related_obj = models.ForeignKey(MyRelatedModel, null=True)
