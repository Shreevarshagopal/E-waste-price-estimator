// Price Calculator Module
class PriceCalculator {
    constructor() {
        this.form = document.getElementById('priceCalculatorForm');
        this.priceResult = document.getElementById('priceResult');
        this.initialMessage = document.getElementById('initialMessage');
        this.errorMessage = document.getElementById('errorMessage');
        
        // Price display elements
        this.totalPriceElement = document.getElementById('totalPrice');
        this.basePriceElement = document.getElementById('basePrice');
        this.deviceAgeElement = document.getElementById('deviceAge');
        this.deviceConditionElement = document.getElementById('deviceCondition');
        this.materialValueElement = document.getElementById('materialValue');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.calculatePrice();
        });
    }

    async calculatePrice() {
        try {
            // Get selected model data
            const modelSelect = document.getElementById('model');
            const selectedOption = modelSelect.options[modelSelect.selectedIndex];
            
            if (!selectedOption || !selectedOption.value) {
                throw new Error('Please select a device model');
            }

            // Get form data
            const formData = new FormData(this.form);
            
            // Add base price from the selected model's data attribute
            formData.append('base_price', selectedOption.dataset.basePrice);
            formData.append('release_year', selectedOption.dataset.releaseYear);

            // Show loading state
            this.setLoading(true);
            
            const response = await fetch('/calculator/calculate/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to calculate price. Please try again.');
            }

            const data = await response.json();
            
            if (data.success) {
                this.displayPrice(data);
            } else {
                throw new Error(data.error || 'Failed to calculate price');
            }
        } catch (error) {
            console.error('Price calculation error:', error);
            this.showError(error.message);
        } finally {
            this.setLoading(false);
        }
    }

    displayPrice(data) {
        // Format currency values
        const formatCurrency = (value) => {
            return new Intl.NumberFormat('en-IN', {
                style: 'currency',
                currency: 'INR'
            }).format(value);
        };

        // Update price display
        this.totalPriceElement.textContent = formatCurrency(data.total_price);
        this.basePriceElement.textContent = formatCurrency(data.base_price);
        this.deviceAgeElement.textContent = data.age;
        this.deviceConditionElement.textContent = this.formatCondition(data.condition);

        // Display material values
        if (data.material_values) {
            let materialHtml = '<ul class="list-unstyled">';
            for (const [material, value] of Object.entries(data.material_values)) {
                materialHtml += `
                    <li class="mb-2">
                        <i class="fas fa-recycle me-2"></i>
                        <strong>${this.formatMaterialName(material)}:</strong> 
                        ${formatCurrency(value)}
                    </li>`;
            }
            materialHtml += '</ul>';
            this.materialValueElement.innerHTML = materialHtml;
        }

        // Show the price result section
        this.errorMessage.classList.add('d-none');
        this.initialMessage.classList.add('d-none');
        this.priceResult.classList.remove('d-none');
    }

    formatCondition(condition) {
        const conditions = {
            'working': 'Working (100%)',
            'partially_working': 'Partially Working (60%)',
            'not_working': 'Not Working (30%)'
        };
        return conditions[condition] || condition;
    }

    formatMaterialName(material) {
        return material.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    setLoading(isLoading) {
        const submitButton = this.form.querySelector('button[type="submit"]');
        if (isLoading) {
            this.form.classList.add('loading');
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Calculating...';
        } else {
            this.form.classList.remove('loading');
            submitButton.disabled = false;
            submitButton.textContent = 'Calculate Price';
        }
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.classList.remove('d-none');
        this.priceResult.classList.add('d-none');
        this.initialMessage.classList.add('d-none');
    }

    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
}

// Initialize the price calculator when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const priceCalculator = new PriceCalculator();
    
    // Make it globally accessible for debugging if needed
    window.priceCalculator = priceCalculator;
});
