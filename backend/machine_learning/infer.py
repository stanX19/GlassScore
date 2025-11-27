import joblib
import pandas as pd
import os
import numpy as np

def load_model():
    model_path = os.path.join(os.path.dirname(__file__), 'loan_model.joblib')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}. Please run train.py first.")
    return joblib.load(model_path)

def predict_loan_status(input_data):
    """
    Predict loan status for a single input or batch.
    input_data: dict or pd.DataFrame
    """
    model = load_model()
    
    if isinstance(input_data, dict):
        input_data = pd.DataFrame([input_data])
    
    # Ensure columns match training data (order doesn't matter for ColumnTransformer usually, but good practice)
    # The model pipeline handles preprocessing
    
    prediction = model.predict(input_data)
    probability = model.predict_proba(input_data)[:, 1]
    
    return prediction, probability

if __name__ == '__main__':
    # Sample input based on train.csv structure
    sample_input = {
        'person_age': 30,
        'person_income': 50000,
        'person_home_ownership': 'RENT',
        'person_emp_length': 5.0,
        'loan_intent': 'EDUCATION',
        'loan_grade': 'B',
        'loan_amnt': 10000,
        'loan_int_rate': 10.0,
        'loan_percent_income': 0.2,
        'cb_person_default_on_file': 'N',
        'cb_person_cred_hist_length': 3
    }
    
    print("Running inference on sample input:")
    print(sample_input)
    
    try:
        pred, prob = predict_loan_status(sample_input)
        print(f"\nPrediction: {pred[0]} (0=Non-Default, 1=Default)")
        print(f"Probability of Default: {prob[0]:.4f}")
    except Exception as e:
        print(f"Error: {e}")