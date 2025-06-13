import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path
import os

# Get the current directory
current_dir = Path(__file__).parent

# Create ml_models directory if it doesn't exist
ml_models_dir = current_dir / 'ml_models'
ml_models_dir.mkdir(exist_ok=True)

# Sample data for e-waste price prediction
def generate_sample_data(n_samples=1000):
    np.random.seed(42)
    
    # Device types: phone=0, laptop=1, tablet=2, desktop=3, tv=4, console=5
    device_types = np.random.randint(0, 6, n_samples)
    
    # Generate ages between 0 and 10 years
    ages = np.random.uniform(0, 10, n_samples)
    
    # Conditions: working=2, partially_working=1, not_working=0
    conditions = np.random.randint(0, 3, n_samples)
    
    # Battery status: good=2, average=1, poor=0, na=1
    battery_status = np.random.randint(0, 3, n_samples)
    
    # Screen condition: good=2, average=1, poor=0, na=1
    screen_condition = np.random.randint(0, 3, n_samples)
    
    # Motherboard status: good=2, average=1, poor=0, na=1
    mb_status = np.random.randint(0, 3, n_samples)
    
    # Base prices for different device types
    base_prices = {
        0: 5000,  # phone
        1: 15000, # laptop
        2: 8000,  # tablet
        3: 20000, # desktop
        4: 12000, # tv
        5: 10000  # console
    }
    
    # Calculate prices
    prices = []
    for i in range(n_samples):
        # Start with base price for device type
        price = base_prices[device_types[i]]
        
        # Adjust for age (decrease by 10% per year)
        price *= (1 - 0.1 * ages[i])
        
        # Adjust for condition
        condition_multiplier = {2: 1.0, 1: 0.6, 0: 0.3}
        price *= condition_multiplier[conditions[i]]
        
        # Adjust for component status
        if battery_status[i] == 2:  # good
            price *= 1.1
        elif battery_status[i] == 0:  # poor
            price *= 0.9
        
        if screen_condition[i] == 2:  # good
            price *= 1.2
        elif screen_condition[i] == 0:  # poor
            price *= 0.7
        
        if mb_status[i] == 2:  # good
            price *= 1.2
        elif mb_status[i] == 0:  # poor
            price *= 0.6
        
        prices.append(max(price, 100))  # Ensure minimum price of 100
    
    # Create feature matrix
    X = np.column_stack([
        device_types,
        ages,
        conditions,
        battery_status,
        screen_condition,
        mb_status
    ])
    
    return X, np.array(prices)

if __name__ == '__main__':
    print("Generating training data...")
    X, y = generate_sample_data()

    print("Splitting data into training and testing sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("Training the model...")
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)

    # Evaluate the model
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)

    print(f"Training R² score: {train_score:.4f}")
    print(f"Testing R² score: {test_score:.4f}")

    # Save the model and scaler
    model_path = ml_models_dir / 'ewaste_price_model.pkl'
    scaler_path = ml_models_dir / 'ewaste_price_scaler.pkl'

    print("\nSaving model and scaler...")
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"Model saved to {model_path}")
    print(f"Scaler saved to {scaler_path}")

    # Print feature importance
    feature_names = ['Device Type', 'Age', 'Condition', 'Battery Status', 
                    'Screen Condition', 'Motherboard Status']
    coefficients = pd.DataFrame(
        {'Feature': feature_names, 'Coefficient': model.coef_}
    ).sort_values('Coefficient', key=abs, ascending=False)

    print("\nFeature Importance:")
    print(coefficients)
