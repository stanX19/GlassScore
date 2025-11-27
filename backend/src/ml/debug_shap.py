import joblib
import pandas as pd
import os
import shap
import numpy as np

# Load model
model_path = os.path.join(os.path.dirname(__file__), 'models', 'loan_model.joblib')
model = joblib.load(model_path)

# Test with different inputs
test_cases = [
    {
        'person_age': 30,
        'person_income': 50000,
        'person_home_ownership': 'RENT',
        'person_emp_length': 5.0,
        'loan_intent': 'EDUCATION',
        'loan_grade': 'B',
        'loan_amnt': 10000000000000000000,
        'loan_int_rate': 10.0,
        'cb_person_default_on_file': 'N',
        'cb_person_cred_hist_length': 3
    },
    {
        'person_age': 45,
        'person_income': 120000,
        'person_home_ownership': 'OWN',
        'person_emp_length': 15.0,
        'loan_intent': 'MEDICAL',
        'loan_grade': 'A',
        'loan_amnt': 5000,
        'loan_int_rate': 5.5,
        'cb_person_default_on_file': 'N',
        'cb_person_cred_hist_length': 20
    },
    {
        'person_age': 25,
        'person_income': 30000,
        'person_home_ownership': 'RENT',
        'person_emp_length': 1.0,
        'loan_intent': 'DEBTCONSOLIDATION',
        'loan_grade': 'D',
        'loan_amnt': 15000,
        'loan_int_rate': 18.0,
        'cb_person_default_on_file': 'Y',
        'cb_person_cred_hist_length': 2
    }
]

preprocessor = model.named_steps['preprocessor']

# Get feature names
numerical_cols = ['person_age', 'person_income', 'person_emp_length',
                 'loan_amnt', 'loan_int_rate', 'loan_percent_income',
                 'cb_person_cred_hist_length']

feature_names = numerical_cols.copy()
cat_features = preprocessor.named_transformers_['cat']
if hasattr(cat_features.named_steps['onehot'], 'get_feature_names_out'):
    cat_feature_names = cat_features.named_steps['onehot'].get_feature_names_out()
    feature_names.extend(cat_feature_names)

print(f"Total features: {len(feature_names)}")
print(f"Feature names: {feature_names}\n")

# Create SHAP explainer
explainer = shap.TreeExplainer(model.named_steps['classifier'])

for i, test_case in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST CASE {i}:")
    print(f"{'='*80}")
    
    input_df = pd.DataFrame([test_case])
    
    # Add derived feature
    if 'loan_amnt' in input_df.columns and 'person_income' in input_df.columns:
        input_df['loan_percent_income'] = input_df['loan_amnt'] / input_df['person_income']
    
    print(f"\nInput:")
    for key, val in test_case.items():
        print(f"  {key}: {val}")
    print(f"  loan_percent_income: {input_df['loan_percent_income'].iloc[0]:.4f}")
    
    # Get preprocessed data
    preprocessed_data = preprocessor.transform(input_df)
    
    # Get SHAP values
    shap_values = explainer.shap_values(preprocessed_data)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    
    if len(shap_values.shape) > 1:
        sample_shap_values = shap_values[0]
    else:
        sample_shap_values = shap_values
    
    sample_shap_values = np.atleast_1d(sample_shap_values).flatten()
    
    # Get prediction
    pred = model.predict(input_df)[0]
    prob = model.predict_proba(input_df)[0, 1]
    
    print(f"\nPrediction: {pred} (Probability: {prob:.4f})")
    print(f"\nTop 10 SHAP values:")
    
    sorted_indices = np.argsort(np.abs(sample_shap_values))[::-1][:10]
    for rank, idx in enumerate(sorted_indices, 1):
        idx = int(idx)
        feature = feature_names[idx]
        shap_val = sample_shap_values[idx]
        print(f"  {rank}. {feature}: {shap_val:.6f} (abs: {abs(shap_val):.6f})")
