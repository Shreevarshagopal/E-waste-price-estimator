from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
import logging
from .forms import UserRegistrationForm, EWasteItemForm, CollectionScheduleForm
from .models import EWasteItem, CollectionSchedule, PriceEstimation, DeviceModel, MaterialPrice, DeviceModelComponent, DeviceBrand
from decimal import Decimal
from django.http import JsonResponse
from .ml_model import EWastePricePredictor
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from django.views.decorators.http import require_http_methods
from .image_analysis import EwasteImageAnalyzer
import cv2

# Configure logging
logger = logging.getLogger(__name__)

# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'ewaste/register.html', {'form': form})

@login_required
def dashboard(request):
    # Get all user items
    user_items = EWasteItem.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate statistics
    total_value = user_items.aggregate(total=Sum('price_estimation'))['total'] or 0
    scheduled_collections = CollectionSchedule.objects.filter(user=request.user).count()
    
    context = {
        'items': user_items,
        'total_value': total_value,
        'scheduled_collections': scheduled_collections
    }
    
    return render(request, 'ewaste/dashboard.html', context)

@login_required
def submit_ewaste(request):
    if request.method == 'POST':
        form = EWasteItemForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                ewaste_item = form.save(commit=False)
                ewaste_item.user = request.user

                # Handle image upload and validation first
                if 'image' not in request.FILES:
                    messages.error(request, 'Please upload an image of your device')
                    return render(request, 'ewaste/submit_ewaste.html', {'form': form})

                image = request.FILES['image']
                
                # Validate image size and type
                if image.size > 5 * 1024 * 1024:  # 5MB limit
                    messages.error(request, 'Image size should not exceed 5MB')
                    return render(request, 'ewaste/submit_ewaste.html', {'form': form})
                
                allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
                if image.content_type not in allowed_types:
                    messages.error(request, 'Only JPEG and PNG images are allowed')
                    return render(request, 'ewaste/submit_ewaste.html', {'form': form})

                ewaste_item.image = image
                ewaste_item.save()  # Initial save to get the image path

                try:
                    # Initialize analyzer and analyze image
                    analyzer = EwasteImageAnalyzer()
                    img_cv, detections = analyzer.analyze_image(ewaste_item.image.path)
                    
                    # Store analysis results
                    ewaste_item.analysis_results = json.dumps(detections)
                    
                    # Save the analyzed image
                    analyzed_image_path = ewaste_item.image.path.replace('.', '_analyzed.')
                    cv2.imwrite(analyzed_image_path, img_cv)
                    ewaste_item.analyzed_image = analyzed_image_path

                    # Calculate price estimation
                    ewaste_item.price_estimation = calculate_price_estimation(
                        ewaste_item.item_type,
                        ewaste_item.functional_status,
                        ewaste_item.age,
                        ewaste_item.battery_status,
                        ewaste_item.screen_condition,
                        ewaste_item.motherboard_status
                    )
                    
                    ewaste_item.save()
                    messages.success(request, 'E-waste item submitted and analyzed successfully!')
                    return redirect('schedule_collection', item_id=ewaste_item.id)
                    
                except Exception as e:
                    # Log the specific analysis error
                    logger.error(f'Error during image analysis: {str(e)}')
                    messages.error(request, 'Error analyzing the image. Please try again.')
                    ewaste_item.delete()  # Clean up the partially created record
                    return render(request, 'ewaste/submit_ewaste.html', {'form': form})
                    
            except Exception as e:
                logger.error(f'Error processing e-waste submission: {str(e)}')
                messages.error(request, 'An error occurred while processing your submission. Please try again.')
                return render(request, 'ewaste/submit_ewaste.html', {'form': form})
    else:
        form = EWasteItemForm()
    
    return render(request, 'ewaste/submit_ewaste.html', {'form': form})

@login_required
def schedule_collection(request, item_id):
    ewaste_item = EWasteItem.objects.get(id=item_id, user=request.user)
    
    if request.method == 'POST':
        form = CollectionScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.user = request.user
            schedule.e_waste_item = ewaste_item
            schedule.save()
            messages.success(request, 'Collection scheduled successfully!')
            return redirect('dashboard')
    else:
        form = CollectionScheduleForm()
    
    return render(request, 'ewaste/schedule_collection.html', {
        'form': form,
        'item': ewaste_item
    })

@login_required
def delete_ewaste(request, item_id):
    try:
        item = EWasteItem.objects.get(id=item_id, user=request.user)
        item.delete()
        messages.success(request, 'E-waste item deleted successfully!')
    except EWasteItem.DoesNotExist:
        messages.error(request, 'E-waste item not found.')
    return redirect('dashboard')

def home(request):
    """Render the home page with basic price calculation information"""
    return render(request, 'ewaste/home.html')

def calculate_price_estimation(item_type, functional_status, age, battery_status, screen_condition, motherboard_status):
    """Calculate estimated price based on item type and various conditions"""
    # Base prices in Indian Rupees
    base_prices = {
        'mobile': Decimal('2000.00'),  # Smartphones
        'laptop': Decimal('5000.00'),  # Laptops
        'tablet': Decimal('1500.00'),  # Tablets
        'tv': Decimal('3000.00'),      # Smart TVs
        'other': Decimal('1000.00'),   # Other devices
    }
    
    # Functional status multipliers
    functional_multipliers = {
        'working': Decimal('0.8'),           # 80% of base price
        'partially_working': Decimal('0.5'),  # 50% of base price
        'damaged': Decimal('0.3'),           # 30% of base price
        'not_working': Decimal('0.1'),       # 10% of base price
    }
    
    # Component status multipliers
    component_multipliers = {
        'good': Decimal('1.0'),
        'bad': Decimal('0.5'),
        'na': Decimal('0.7'),  # Not applicable
    }
    
    # Age depreciation (per year)
    age_depreciation = Decimal('0.1')  # 10% depreciation per year, max 70% depreciation
    
    # Get base price for the item type
    base_price = base_prices.get(item_type, base_prices['other'])
    
    # Apply functional status multiplier
    multiplier = functional_multipliers.get(functional_status, Decimal('0.3'))
    
    # Apply component status multipliers
    battery_multiplier = component_multipliers.get(battery_status, Decimal('0.7'))
    screen_multiplier = component_multipliers.get(screen_condition, Decimal('0.7'))
    motherboard_multiplier = component_multipliers.get(motherboard_status, Decimal('0.7'))
    
    # Calculate average component multiplier
    component_multiplier = (battery_multiplier + screen_multiplier + motherboard_multiplier) / Decimal('3.0')
    
    # Apply age depreciation (max 70% depreciation)
    age_multiplier = max(Decimal('0.3'), Decimal('1.0') - (age * age_depreciation))
    
    # Calculate final price
    estimation = base_price * multiplier * component_multiplier * age_multiplier
    
    return estimation.quantize(Decimal('0.01'))

def calculate_total_material_weight(device_model, material_name):
    """Calculate total weight of a specific material across all components"""
    total_weight = Decimal('0.00')
    
    # Get all components for this device model
    components = DeviceModelComponent.objects.filter(device_model=device_model)
    
    for component in components:
        # Get material percentage for this component (you'll need to implement this)
        material_percentage = get_material_percentage(component, material_name)
        if material_percentage:
            # Add to total weight
            total_weight += component.weight * (material_percentage / 100)
    
    return total_weight

def get_device_models(request):
    """AJAX endpoint to get device models based on brand and type"""
    brand = request.GET.get('brand')
    device_type = request.GET.get('type')
    
    if brand and device_type:
        models = DeviceModel.objects.filter(
            brand__iexact=brand,
            device_type__iexact=device_type
        ).values('id', 'name', 'release_year')
        model_list = [{'id': m['id'], 'name': f"{m['name']} ({m['release_year']})"} for m in models]
        return JsonResponse({'models': model_list})
    return JsonResponse({'models': []})

def get_brands(request):
    """Get brands for a specific device type"""
    device_type = request.GET.get('type')
    if not device_type:
        return JsonResponse({
            'success': False,
            'error': 'Device type is required'
        })
    
    # First, clean up any duplicate brands for this device type
    existing_brands = DeviceBrand.objects.filter(device_type=device_type)
    for brand in existing_brands:
        duplicates = DeviceBrand.objects.filter(
            device_type=device_type,
            name=brand.name
        ).exclude(id=brand.id)
        duplicates.delete()
    
    # Get unique brands for this device type
    brands = list(DeviceBrand.objects.filter(
        device_type=device_type
    ).values_list('name', flat=True).distinct().order_by('name'))
    
    # If no brands found, add test data
    if not brands:
        if device_type == 'phone':
            brands = [
                'Apple', 'Google', 'OnePlus', 'Samsung', 'Xiaomi', 
                'OPPO', 'Vivo', 'Realme', 'Nothing', 'Motorola'
            ]
        elif device_type == 'laptop':
            brands = [
                'Apple', 'Dell', 'HP', 'Lenovo', 'Acer', 
                'ASUS', 'MSI', 'Razer', 'Microsoft', 'LG'
            ]
        elif device_type == 'tablet':
            brands = [
                'Apple', 'Samsung', 'Microsoft', 'Lenovo',
                'Xiaomi', 'HUAWEI', 'Realme', 'OPPO'
            ]
        elif device_type == 'tv':
            brands = [
                'Samsung', 'LG', 'Sony', 'TCL', 'Hisense',
                'OnePlus', 'Xiaomi', 'Vu', 'Panasonic'
            ]
        elif device_type == 'console':
            brands = [
                'Sony', 'Microsoft', 'Nintendo',
                'Sega', 'Atari', 'Steam'
            ]
        
        # Save these brands to the database
        for brand_name in brands:
            DeviceBrand.objects.get_or_create(
                name=brand_name,
                device_type=device_type
            )
        
        # Refresh the brands list
        brands = list(DeviceBrand.objects.filter(
            device_type=device_type
        ).values_list('name', flat=True).distinct().order_by('name'))
    
    return JsonResponse({
        'success': True,
        'brands': brands
    })

def get_models(request):
    """Get models for a specific brand and device type"""
    device_type = request.GET.get('type')
    brand_name = request.GET.get('brand')
    
    if not device_type or not brand_name:
        return JsonResponse({
            'success': False,
            'error': 'Device type and brand are required'
        })
    
    try:
        # Get unique models for this brand and device type
        models = list(DeviceModel.objects.filter(
            device_type=device_type,
            brand__name=brand_name
        ).values('id', 'name', 'release_year', 'base_price').distinct().order_by('-release_year', 'name'))
        
        # If no models found, add test data
        if not models:
            current_year = 2025
            test_models = []
            
            if device_type == 'phone':
                if brand_name == 'Apple':
                    test_models = [
                        ('iPhone 15 Pro Max', current_year, 159900),
                        ('iPhone 15 Pro', current_year, 134900),
                        ('iPhone 15', current_year, 79900),
                        ('iPhone 14 Pro', current_year - 1, 119900),
                        ('iPhone 14', current_year - 1, 69900),
                        ('iPhone 13', current_year - 2, 59900),
                        ('iPhone 12', current_year - 3, 49900)
                    ]
                elif brand_name == 'Samsung':
                    test_models = [
                        ('Galaxy S24 Ultra', current_year, 129900),
                        ('Galaxy S24+', current_year, 99900),
                        ('Galaxy S24', current_year, 79900),
                        ('Galaxy S23 Ultra', current_year - 1, 124900),
                        ('Galaxy S23', current_year - 1, 74900),
                        ('Galaxy A54', current_year - 1, 38900)
                    ]
                elif brand_name == 'Google':
                    test_models = [
                        ('Pixel 8 Pro', current_year, 106900),
                        ('Pixel 8', current_year, 75900),
                        ('Pixel 7a', current_year - 1, 39900),
                        ('Pixel 7', current_year - 1, 59900),
                        ('Pixel 6a', current_year - 2, 29900)
                    ]
                elif brand_name == 'OnePlus':
                    test_models = [
                        ('12', current_year, 64900),
                        ('11', current_year - 1, 56900),
                        ('Nord 3', current_year - 1, 33900),
                        ('10 Pro', current_year - 2, 49900)
                    ]
                elif brand_name == 'Nothing':
                    test_models = [
                        ('Phone (2)', current_year, 44900),
                        ('Phone (1)', current_year - 1, 32900)
                    ]
                elif brand_name == 'Xiaomi':
                    test_models = [
                        ('13 Pro', current_year, 79900),
                        ('12 Pro', current_year - 1, 62900),
                        ('Note 12 Pro', current_year - 1, 29900)
                    ]
                elif brand_name in ['OPPO', 'Vivo', 'Realme']:
                    test_models = [
                        (f'{brand_name} Flagship', current_year, 54900),
                        (f'{brand_name} Mid-range', current_year - 1, 32900),
                        (f'{brand_name} Budget', current_year - 1, 18900)
                    ]
            elif device_type == 'laptop':
                if brand_name == 'Apple':
                    test_models = [
                        ('MacBook Pro 16" M3 Max', current_year, 399900),
                        ('MacBook Pro 14" M3 Pro', current_year, 249900),
                        ('MacBook Air 15" M2', current_year - 1, 154900),
                        ('MacBook Air 13" M1', current_year - 2, 99900)
                    ]
                elif brand_name in ['Dell', 'HP', 'Lenovo']:
                    test_models = [
                        (f'{brand_name} Premium Pro', current_year, 189900),
                        (f'{brand_name} Premium', current_year, 129900),
                        (f'{brand_name} Mid-range', current_year - 1, 79900),
                        (f'{brand_name} Entry', current_year - 2, 49900)
                    ]
                elif brand_name == 'ASUS':
                    test_models = [
                        ('ROG Zephyrus', current_year, 224900),
                        ('TUF Gaming', current_year, 124900),
                        ('VivoBook Pro', current_year - 1, 89900),
                        ('VivoBook', current_year - 1, 54900)
                    ]
                elif brand_name == 'MSI':
                    test_models = [
                        ('Titan', current_year, 399900),
                        ('Raider', current_year, 299900),
                        ('Stealth', current_year - 1, 199900),
                        ('Katana', current_year - 1, 99900)
                    ]
                elif brand_name == 'Razer':
                    test_models = [
                        ('Blade 18', current_year, 399900),
                        ('Blade 16', current_year, 299900),
                        ('Blade 14', current_year - 1, 199900)
                    ]
            elif device_type == 'tablet':
                if brand_name == 'Apple':
                    test_models = [
                        ('iPad Pro 12.9" M2', current_year, 119900),
                        ('iPad Pro 11" M2', current_year, 89900),
                        ('iPad Air M1', current_year - 1, 59900),
                        ('iPad 10th Gen', current_year - 2, 44900)
                    ]
                elif brand_name == 'Samsung':
                    test_models = [
                        ('Galaxy Tab S9 Ultra', current_year, 108900),
                        ('Galaxy Tab S9+', current_year, 89900),
                        ('Galaxy Tab S9', current_year, 74900),
                        ('Galaxy Tab S8', current_year - 1, 58900)
                    ]
                elif brand_name == 'Microsoft':
                    test_models = [
                        ('Surface Pro 9', current_year, 149900),
                        ('Surface Pro 8', current_year - 1, 119900),
                        ('Surface Go 4', current_year, 79900)
                    ]
                elif brand_name in ['Xiaomi', 'Realme', 'OPPO']:
                    test_models = [
                        (f'{brand_name} Premium Tab', current_year, 45900),
                        (f'{brand_name} Mid Tab', current_year - 1, 28900),
                        (f'{brand_name} Basic Tab', current_year - 1, 15900)
                    ]
            elif device_type == 'tv':
                base_prices = {
                    'Samsung': [249900, 199900, 149900, 99900],  # 75", 65", 55", 50"
                    'LG': [239900, 189900, 139900, 89900],
                    'Sony': [299900, 249900, 189900, 129900],
                    'OnePlus': [149900, 119900, 89900, 59900],
                    'TCL': [99900, 79900, 59900, 39900],
                    'Xiaomi': [89900, 69900, 49900, 34900],
                    'Vu': [79900, 59900, 44900, 29900]
                }
                prices = base_prices.get(brand_name, [99900, 79900, 59900, 39900])
                
                test_models = [
                    (f'{brand_name} 75" Premium OLED', current_year, prices[0]),
                    (f'{brand_name} 65" OLED', current_year, prices[1]),
                    (f'{brand_name} 55" QLED', current_year - 1, prices[2]),
                    (f'{brand_name} 50" LED', current_year - 2, prices[3])
                ]
            elif device_type == 'console':
                if brand_name == 'Sony':
                    test_models = [
                        ('PlayStation 5 Pro', current_year, 59900),
                        ('PlayStation 5', current_year - 2, 49900),
                        ('PlayStation 4 Pro', current_year - 6, 29900)
                    ]
                elif brand_name == 'Microsoft':
                    test_models = [
                        ('Xbox Series X', current_year - 2, 49900),
                        ('Xbox Series S', current_year - 2, 29900)
                    ]
                elif brand_name == 'Nintendo':
                    test_models = [
                        ('Switch OLED', current_year - 3, 34900),
                        ('Switch', current_year - 5, 29900),
                        ('Switch Lite', current_year - 4, 19900)
                    ]
                elif brand_name == 'Steam':
                    test_models = [
                        ('Steam Deck OLED', current_year, 54900),
                        ('Steam Deck LCD', current_year - 1, 39900)
                    ]
            
            # Create brand if it doesn't exist
            brand, _ = DeviceBrand.objects.get_or_create(
                name=brand_name,
                device_type=device_type
            )
            
            # Create models
            models = []
            for name, year, price in test_models:
                model = DeviceModel.objects.create(
                    name=name,
                    brand=brand,
                    device_type=device_type,
                    release_year=year,
                    base_price=price
                )
                models.append({
                    'id': model.id,
                    'name': model.name,
                    'release_year': model.release_year,
                    'base_price': float(model.base_price)
                })
        
        return JsonResponse({
            'success': True,
            'models': models
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def calculate_material_value(device_model):
    """Calculate the value of recyclable materials in a device"""
    material_prices = {}
    
    # Base material prices per gram in INR (using Decimal)
    base_prices = {
        'gold': Decimal('5000'),      # INR per gram
        'silver': Decimal('75'),      # INR per gram
        'copper': Decimal('0.8'),     # INR per gram
        'aluminum': Decimal('0.2'),   # INR per gram
        'plastic': Decimal('0.05')    # INR per gram
    }
    
    # Estimated material weights based on device type (using Decimal)
    if device_model.device_type == 'phone':
        weights = {
            'gold': Decimal('0.034'),     # grams
            'silver': Decimal('0.34'),    # grams
            'copper': Decimal('9'),       # grams
            'aluminum': Decimal('25'),    # grams
            'plastic': Decimal('80')      # grams
        }
    elif device_model.device_type == 'laptop':
        weights = {
            'gold': Decimal('0.2'),       # grams
            'silver': Decimal('0.7'),     # grams
            'copper': Decimal('65'),      # grams
            'aluminum': Decimal('250'),   # grams
            'plastic': Decimal('500')     # grams
        }
    elif device_model.device_type == 'tablet':
        weights = {
            'gold': Decimal('0.1'),       # grams
            'silver': Decimal('0.5'),     # grams
            'copper': Decimal('30'),      # grams
            'aluminum': Decimal('150'),   # grams
            'plastic': Decimal('200')     # grams
        }
    elif device_model.device_type == 'tv':
        weights = {
            'gold': Decimal('0.1'),       # grams
            'silver': Decimal('0.5'),     # grams
            'copper': Decimal('450'),     # grams
            'aluminum': Decimal('700'),   # grams
            'plastic': Decimal('3000')    # grams
        }
    else:  # gaming console
        weights = {
            'gold': Decimal('0.15'),      # grams
            'silver': Decimal('0.6'),     # grams
            'copper': Decimal('100'),     # grams
            'aluminum': Decimal('300'),   # grams
            'plastic': Decimal('1000')    # grams
        }
    
    # Calculate value for each material
    material_values = {}
    for material, weight in weights.items():
        price_per_gram = base_prices[material]
        total_value = weight * price_per_gram
        material_values[material] = float(total_value)  # Convert to float for JSON serialization
    
    return material_values

@require_http_methods(['POST'])
def calculate_price(request):
    """Calculate the estimated price for an e-waste device"""
    try:
        data = json.loads(request.body)
        model_id = data.get('model_id')
        condition = data.get('condition')
        age = data.get('age')
        
        # Convert age to Decimal
        age = Decimal(age)
        
        # Get device model
        device_model = DeviceModel.objects.get(id=model_id)
        
        # Get base price from device model
        base_price = device_model.base_price
        
        # Condition multipliers
        condition_multipliers = {
            'working': Decimal('1.00'),           # 100% of base price
            'partially_working': Decimal('0.60'), # 60% of base price
            'not_working': Decimal('0.30'),      # 30% of base price
        }
        
        # Apply condition multiplier
        condition_multiplier = condition_multipliers.get(condition, Decimal('0.30'))
        
        # Calculate age depreciation (up to 80% over 5 years)
        max_age_depreciation = Decimal('0.80')  # Maximum 80% depreciation
        depreciation_per_year = max_age_depreciation / Decimal('5')  # Spread over 5 years
        age_depreciation = min(max_age_depreciation, age * depreciation_per_year)
        age_multiplier = Decimal('1.0') - age_depreciation
        
        # Calculate material value (minimum price floor)
        material_value = calculate_material_value(device_model)
        
        # Calculate final price
        final_price = (base_price * condition_multiplier * age_multiplier)
        
        # Ensure price doesn't go below material value
        final_price = max(final_price, material_value)
        
        # Round to nearest rupee
        final_price = final_price.quantize(Decimal('1.'))
        
        return JsonResponse({
            'success': True,
            'total_price': float(final_price),
            'base_price': float(base_price),
            'age': age,
            'condition': condition,
            'material_values': {
                'metals': float(material_value * Decimal('0.4')),
                'plastics': float(material_value * Decimal('0.3')),
                'electronics': float(material_value * Decimal('0.3'))
            }
        })
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except DeviceModel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Device model not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)

def price_calculator(request):
    """Render the price calculator page"""
    return render(request, 'ewaste/price_calculator.html')

def reuse_guide(request):
    """View for displaying e-waste reuse guidelines and tips."""
    return render(request, 'ewaste/reuse_guide.html')

def about(request):
    return render(request, 'ewaste/about.html')

def contact(request):
    return render(request, 'ewaste/contact.html')
