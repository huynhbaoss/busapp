from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField


# Create your models here.

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    avatar = models.ImageField(upload_to='users/%Y/%m/', null=True)
    role = models.CharField(choices=[('A', 'Admin'), ('U', 'User'), ('E', 'Employee')], max_length=1, default='C',
                            null=True)
    is_verified = models.BooleanField(default=False)


class TransportCompany(models.Model):
    name = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20)
    description = RichTextField(null=True)
    is_active = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatar/%Y/%m', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='busapp')

    def __str__(self):
        return self.name


class Buses(BaseModel):
    name = models.CharField(max_length=255)
    start_point = models.CharField(max_length=100)
    end_point = models.CharField(max_length=100)
    departure_time = models.CharField(max_length=100, default='')
    arrival_time = models.CharField(max_length=100, default='')
    available_seats = models.IntegerField()
    is_available = models.BooleanField(default=True)
    description = RichTextField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=3)
    transport_company = models.ForeignKey(TransportCompany, on_delete=models.CASCADE)
    revenue = models.FloatField(default=0.0)

    def __str__(self):
        return self.name


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    buses = models.ForeignKey(Buses, on_delete=models.CASCADE)
    is_paid = models.BooleanField(default=False)
    booking_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.buses}'


class Seat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=20)
    is_booked = models.BooleanField(default=False)
    route = models.ForeignKey(Buses, on_delete=models.CASCADE)


class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50)
    payment_status = models.BooleanField(default=False)
    payment_time = models.DateTimeField(auto_now_add=True)
    amount = models.IntegerField()

    def __str__(self):
        return f'{self.booking} - {self.payment_method} - {self.amount}'

    PAYMENT_METHOD = (
        ('by-cash', 'By-Cash'),
        ('online', 'Online')
    )
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD, default='by-cash')


class ActionBase(BaseModel):
    buses = models.ForeignKey(Buses, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Review(ActionBase):
    rate = models.SmallIntegerField(default=0)
    content = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('buses', 'user')

    def __str__(self):
        return self.content


class Comment(ActionBase):
    content = models.CharField(max_length=255)
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.content


class Delivery(models.Model):
    sender_name = models.CharField(max_length=100)
    sender_phone = models.CharField(max_length=20)
    receiver_name = models.CharField(max_length=100)
    receiver_phone = models.CharField(max_length=20)
    buses = models.ForeignKey(Buses, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='Pending')

    def __str__(self):
        return f'{self.sender_name} -> {self.receiver_name} ({self.status})'


class Notification(models.Model):
    sender = models.IntegerField()
    content = models.CharField(max_length=255)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content
