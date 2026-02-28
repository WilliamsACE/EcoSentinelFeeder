from django.db import models


class Feeder(models.Model):
    feeder_id  = models.CharField(max_length=20, unique=True)
    name       = models.CharField(max_length=100)
    location   = models.CharField(max_length=200)
    lat        = models.FloatField(default=0)
    lng        = models.FloatField(default=0)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.feeder_id} — {self.name}"


class FeederStatus(models.Model):
    STATUS = [('online','En línea'),('warn','Alerta'),('offline','Sin conexión')]

    feeder      = models.ForeignKey(Feeder, on_delete=models.CASCADE, related_name='statuses')
    status      = models.CharField(max_length=10, choices=STATUS, default='online')
    battery     = models.IntegerField(default=0)
    food_dog    = models.IntegerField(default=0)
    food_cat    = models.IntegerField(default=0)
    water       = models.IntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        get_latest_by = 'recorded_at'


class DetectionEvent(models.Model):
    SPECIES = [('perro','Perro'),('gato','Gato'),('alerta','Alerta')]

    feeder      = models.ForeignKey(Feeder, on_delete=models.CASCADE, related_name='events')
    species     = models.CharField(max_length=10, choices=SPECIES)
    grams       = models.IntegerField(default=0)
    confidence  = models.IntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']