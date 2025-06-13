document.addEventListener('DOMContentLoaded', function() {
    const deviceTypeSelect = document.getElementById('id_item_type');
    const brandInput = document.getElementById('id_brand');
    const modelInput = document.getElementById('id_model');
    const batteryStatusSelect = document.getElementById('id_battery_status');
    const screenConditionSelect = document.getElementById('id_screen_condition');
    const motherboardStatusSelect = document.getElementById('id_motherboard_status');

    // Store device brands and models data
    const deviceData = {
        smartphone: {
            brands: ['Apple', 'Samsung', 'OnePlus', 'Xiaomi', 'Google', 'Oppo', 'Vivo', 'Realme'],
            models: {
                'Apple': ['iPhone 15 Pro Max', 'iPhone 15 Pro', 'iPhone 15', 'iPhone 14 Pro Max', 'iPhone 14 Pro', 'iPhone 14', 'iPhone 13 Pro Max', 'iPhone 13'],
                'Samsung': ['Galaxy S23 Ultra', 'Galaxy S23+', 'Galaxy S23', 'Galaxy S22 Ultra', 'Galaxy S22+', 'Galaxy A54', 'Galaxy A34'],
                'OnePlus': ['11 5G', '10 Pro', '10T', 'Nord 3', 'Nord CE 3', 'Nord N30'],
                'Xiaomi': ['13 Pro', '13', '12 Pro', '12', 'Redmi Note 12 Pro+', 'Redmi Note 12 Pro'],
                'Google': ['Pixel 8 Pro', 'Pixel 8', 'Pixel 7 Pro', 'Pixel 7', 'Pixel 6a'],
                'Oppo': ['Find X6 Pro', 'Find X6', 'Reno 10 Pro+', 'Reno 10 Pro', 'Reno 10'],
                'Vivo': ['X90 Pro+', 'X90 Pro', 'X90', 'V29 Pro', 'V29'],
                'Realme': ['11 Pro+', '11 Pro', 'GT Neo 5', 'GT 3', 'GT Neo 3']
            }
        },
        laptop: {
            brands: ['Apple', 'Dell', 'HP', 'Lenovo', 'Asus', 'Acer', 'MSI', 'Microsoft'],
            models: {
                'Apple': ['MacBook Pro 16"', 'MacBook Pro 14"', 'MacBook Pro 13"', 'MacBook Air M2', 'MacBook Air M1'],
                'Dell': ['XPS 15', 'XPS 13', 'Latitude 7430', 'Inspiron 15', 'Precision 5570'],
                'HP': ['Spectre x360', 'Envy x360', 'Pavilion 15', 'EliteBook 840', 'ProBook 450'],
                'Lenovo': ['ThinkPad X1 Carbon', 'ThinkPad T14', 'IdeaPad 5', 'Yoga 9i', 'Legion 5'],
                'Asus': ['ROG Zephyrus G14', 'ROG Strix', 'ZenBook 14', 'TUF Gaming A15', 'VivoBook 15'],
                'Acer': ['Predator Helios 300', 'Swift 5', 'Aspire 5', 'Nitro 5', 'ConceptD 7'],
                'MSI': ['GE76 Raider', 'GS66 Stealth', 'Creator Z16', 'Prestige 14', 'Modern 14'],
                'Microsoft': ['Surface Laptop 5', 'Surface Laptop 4', 'Surface Book 3', 'Surface Laptop Studio', 'Surface Laptop Go 2']
            }
        },
        tablet: {
            brands: ['Apple', 'Samsung', 'Microsoft', 'Lenovo', 'Huawei'],
            models: {
                'Apple': ['iPad Pro 12.9"', 'iPad Pro 11"', 'iPad Air', 'iPad mini', 'iPad'],
                'Samsung': ['Galaxy Tab S9 Ultra', 'Galaxy Tab S9+', 'Galaxy Tab S9', 'Galaxy Tab S8', 'Galaxy Tab A8'],
                'Microsoft': ['Surface Pro 9', 'Surface Pro 8', 'Surface Pro 7+', 'Surface Go 3'],
                'Lenovo': ['Tab P12 Pro', 'Tab P11 Pro', 'Tab M10 Plus', 'Yoga Tab 11'],
                'Huawei': ['MatePad Pro', 'MatePad 11', 'MatePad 10.4', 'MatePad T10s']
            }
        },
        tv: {
            brands: ['Samsung', 'LG', 'Sony', 'TCL', 'Hisense'],
            models: {
                'Samsung': ['Neo QLED 8K', 'Neo QLED 4K', 'QLED', 'Crystal UHD'],
                'LG': ['OLED G3', 'OLED C3', 'QNED', 'NanoCell'],
                'Sony': ['Bravia XR A95K', 'Bravia XR X95K', 'Bravia X85K'],
                'TCL': ['6-Series', '5-Series', '4-Series'],
                'Hisense': ['U8K', 'U7K', 'U6K']
            }
        },
        'gaming console': {
            brands: ['Sony', 'Microsoft', 'Nintendo'],
            models: {
                'Sony': ['PlayStation 5', 'PlayStation 4 Pro', 'PlayStation 4'],
                'Microsoft': ['Xbox Series X', 'Xbox Series S', 'Xbox One X', 'Xbox One S'],
                'Nintendo': ['Switch OLED', 'Switch', 'Switch Lite']
            }
        }
    };

    // Function to update brand options
    function updateBrands(deviceType) {
        const brands = deviceData[deviceType]?.brands || [];
        brandInput.value = ''; // Clear current value
        brandInput.placeholder = brands.length ? 'Select from: ' + brands.join(', ') : 'Enter brand name';

        // Create datalist for brand suggestions
        let datalistId = 'brandSuggestions';
        let datalist = document.getElementById(datalistId);
        if (!datalist) {
            datalist = document.createElement('datalist');
            datalist.id = datalistId;
            brandInput.parentNode.appendChild(datalist);
            brandInput.setAttribute('list', datalistId);
        }
        datalist.innerHTML = brands.map(brand => `<option value="${brand}">`).join('');
    }

    // Function to update model options
    function updateModels(deviceType, brand) {
        const models = deviceData[deviceType]?.models[brand] || [];
        modelInput.value = ''; // Clear current value
        modelInput.placeholder = models.length ? 'Select from: ' + models.join(', ') : 'Enter model name';

        // Create datalist for model suggestions
        let datalistId = 'modelSuggestions';
        let datalist = document.getElementById(datalistId);
        if (!datalist) {
            datalist = document.createElement('datalist');
            datalist.id = datalistId;
            modelInput.parentNode.appendChild(datalist);
            modelInput.setAttribute('list', datalistId);
        }
        datalist.innerHTML = models.map(model => `<option value="${model}">`).join('');
    }

    // Function to update component fields based on device type
    function updateComponentFields(deviceType) {
        if (!deviceType) return;

        // Reset all components to enabled and 'good' state
        [screenConditionSelect, batteryStatusSelect, motherboardStatusSelect].forEach(select => {
            select.disabled = false;
            select.value = 'good';
        });

        // Adjust components based on device type
        switch (deviceType) {
            case 'tv':
                // TVs don't have batteries
                batteryStatusSelect.value = 'na';
                batteryStatusSelect.disabled = true;
                break;
            case 'gaming console':
                // Gaming consoles don't have screens
                screenConditionSelect.value = 'na';
                screenConditionSelect.disabled = true;
                break;
        }
    }

    // Event listeners
    deviceTypeSelect.addEventListener('change', function() {
        const selectedType = this.value.toLowerCase();
        updateBrands(selectedType);
        updateModels(selectedType, brandInput.value);
        updateComponentFields(selectedType);
    });

    brandInput.addEventListener('input', function() {
        const selectedType = deviceTypeSelect.value.toLowerCase();
        const selectedBrand = this.value;
        updateModels(selectedType, selectedBrand);
    });

    // Initialize dropdowns if values are pre-selected
    if (deviceTypeSelect.value) {
        const selectedType = deviceTypeSelect.value.toLowerCase();
        updateBrands(selectedType);
        updateComponentFields(selectedType);
        if (brandInput.value) {
            updateModels(selectedType, brandInput.value);
        }
    }
});
