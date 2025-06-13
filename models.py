from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone


class DeviceComponent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    recyclable = models.BooleanField(default=True)
    hazardous = models.BooleanField(default=False)
    handling_instructions = models.TextField(blank=True)
    
    # Material composition percentages (should not exceed 100%)
    copper_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gold_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    silver_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    plastic_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    aluminum_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    steel_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        total_percentage = (
            self.copper_percentage + self.gold_percentage + self.silver_percentage +
            self.plastic_percentage + self.aluminum_percentage + self.steel_percentage
        )
        if total_percentage > 100:
            raise ValidationError("Total material percentage cannot exceed 100%")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class DeviceBrand(models.Model):
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50)  # mobile, laptop, tv, etc.

    def __str__(self):
        return f"{self.name} ({self.device_type})"

    class Meta:
        unique_together = ('name', 'device_type')

class DeviceModel(models.Model):
    DEVICE_TYPES = [
        ('phone', 'Smartphone'),
        ('laptop', 'Laptop'),
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop'),
        ('tv', 'Television'),
        ('console', 'Gaming Console'),
        ('printer', 'Printer'),
        ('monitor', 'Monitor'),
        ('camera', 'Digital Camera'),
        ('router', 'Router/Modem'),
        ('speaker', 'Speaker/Audio'),
        ('smartwatch', 'Smartwatch'),
        ('earbuds', 'Wireless Earbuds'),
        ('keyboard', 'Keyboard'),
        ('mouse', 'Mouse'),
        ('server', 'Server'),
        ('ups', 'UPS/Power Supply'),
        ('projector', 'Projector'),
        ('scanner', 'Scanner'),
        ('other', 'Other Electronics')
    ]

    brand = models.ForeignKey(DeviceBrand, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES, db_index=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    release_year = models.IntegerField()

    class Meta:
        unique_together = ['brand', 'name']

    def __str__(self):
        return f"{self.brand.name} {self.name} ({self.release_year})"

class MaterialPrice(models.Model):
    material_name = models.CharField(max_length=100, unique=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.material_name} (₹{self.price_per_unit}/unit)"

class DeviceModelComponent(models.Model):
    device_model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, related_name='device_components')
    component_name = models.CharField(max_length=100)
    material_name = models.CharField(max_length=100)
    weight = models.DecimalField(max_digits=10, decimal_places=6, default=0.00)

    def __str__(self):
        return f"{self.device_model} - {self.component_name} ({self.material_name})"

    class Meta:
        unique_together = ['device_model', 'component_name', 'material_name']

# EWaste Item Model
class EWasteItem(models.Model):
    FUNCTIONAL_STATUS = [
        ('working', 'Fully Working'),
        ('partial', 'Partially Working'),
        ('not_working', 'Not Working')
    ]
    
    COMPONENT_STATUS = [
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'Not Applicable')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=100)
    age = models.IntegerField()
    functional_status = models.CharField(max_length=50, choices=FUNCTIONAL_STATUS)
    battery_status = models.CharField(max_length=50, choices=COMPONENT_STATUS, null=True, blank=True)
    screen_condition = models.CharField(max_length=50, choices=COMPONENT_STATUS, null=True, blank=True)
    motherboard_status = models.CharField(max_length=50, choices=COMPONENT_STATUS, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='ewaste_images/')
    analyzed_image = models.ImageField(upload_to='analyzed_images/', null=True, blank=True)
    analysis_results = models.JSONField(null=True, blank=True)
    price_estimation = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.item_type} - {self.brand} {self.model}"

class CollectionSchedule(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    e_waste_item = models.OneToOneField(EWasteItem, on_delete=models.CASCADE, related_name='collection_schedule')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    preferred_date = models.DateField(default=timezone.now)
    preferred_time = models.TimeField(default=timezone.now)
    pickup_address = models.TextField(default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_status_color(self):
        """Return Bootstrap color class based on status"""
        status_colors = {
            'pending': 'warning',
            'confirmed': 'primary',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return status_colors.get(self.status, 'secondary')
    
    def __str__(self):
        return f"Collection for {self.e_waste_item} - {self.get_status_display()}"

class PriceHistory(models.Model):
    device_model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)
    market_condition = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.device_model} - ₹{self.base_price} ({self.recorded_at.date()})"

class PriceEstimation(models.Model):
    COMPONENT_TYPES = [
        ('copper', 'Copper'),
        ('plastic', 'Plastic'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('aluminum', 'Aluminum'),
        ('other', 'Other'),
    ]
    
    item_type = models.CharField(max_length=50, db_index=True)
    component = models.CharField(max_length=50, choices=COMPONENT_TYPES)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit = models.CharField(max_length=20, default='kg')
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['item_type', 'component']

    def __str__(self):
        return f"{self.get_component_display()} price for {self.item_type}"

@receiver(pre_save, sender=DeviceModel)
def update_price_history(sender, instance, **kwargs):
    """Create price history entry when base price changes"""
    try:
        old_instance = DeviceModel.objects.get(pk=instance.pk)
        if old_instance.base_price != instance.base_price:
            PriceHistory.objects.create(
                device_model=instance,
                base_price=instance.base_price,
                market_condition='Normal',  # You might want to make this configurable
                notes='Automatic price history entry'
            )
    except DeviceModel.DoesNotExist:
        # This is a new instance, no need to create history
        pass
