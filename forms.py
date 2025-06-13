from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import EWasteItem, CollectionSchedule, DeviceModel

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class EWasteItemForm(forms.ModelForm):
    class Meta:
        model = EWasteItem
        fields = [
            'item_type', 
            'brand', 
            'model', 
            'age',
            'functional_status',
            'battery_status',
            'screen_condition',
            'motherboard_status',
            'description',
            'image'
        ]
        widgets = {
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Samsung, Apple, Dell'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Galaxy S21, MacBook Pro'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter age in years'}),
            'functional_status': forms.Select(attrs={'class': 'form-select'}),
            'battery_status': forms.Select(attrs={'class': 'form-select'}),
            'screen_condition': forms.Select(attrs={'class': 'form-select'}),
            'motherboard_status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide any additional details about your device'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'item_type': 'Device Type',
            'functional_status': 'Device Working Condition',
            'battery_status': 'Battery Condition',
            'screen_condition': 'Screen Condition',
            'motherboard_status': 'Motherboard Condition',
        }
        help_texts = {
            'age': 'How old is your device?',
            'functional_status': 'Select the current working state of your device',
            'battery_status': 'Select NA if not applicable',
            'screen_condition': 'Select NA if not applicable',
            'motherboard_status': 'Select NA if not applicable',
            'image': 'Upload a clear image of your device (JPEG or PNG, max 5MB)'
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError("Image size should not exceed 5MB")
            if not image.content_type in ['image/jpeg', 'image/png', 'image/jpg']:
                raise forms.ValidationError("Only JPEG and PNG images are allowed")
        return image

class PriceCalculatorForm(forms.Form):
    item_type = forms.ChoiceField(
        choices=DeviceModel.DEVICE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    brand = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Samsung, Apple, Dell'})
    )
    model = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Galaxy S21, MacBook Pro'})
    )
    age = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter age in years'}),
        min_value=0
    )
    functional_status = forms.ChoiceField(
        choices=EWasteItem.FUNCTIONAL_STATUS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    battery_status = forms.ChoiceField(
        choices=EWasteItem.COMPONENT_STATUS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    screen_condition = forms.ChoiceField(
        choices=EWasteItem.COMPONENT_STATUS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    motherboard_status = forms.ChoiceField(
        choices=EWasteItem.COMPONENT_STATUS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class CollectionScheduleForm(forms.ModelForm):
    class Meta:
        model = CollectionSchedule
        fields = ['preferred_date', 'preferred_time', 'pickup_address']
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'preferred_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
