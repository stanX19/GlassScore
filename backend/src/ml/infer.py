import joblib
import pandas as pd
import os
import shap
import numpy as np
from src.models.ml_model import LoanApplication

def load_model():
    # Updated path to models directory
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'loan_model.joblib')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}. Please run train.py first.")
    return joblib.load(model_path)

def explain_prediction(input_data: pd.DataFrame, model) -> str:
    """
    Generate human-readable explanation for the prediction using SHAP.
    Returns top 2 feature contributions as a formatted string.
    Only shows features that are actually present in the input.
    """
    try:
        # Get the preprocessed data
        preprocessor = model.named_steps['preprocessor']
        preprocessed_data = preprocessor.transform(input_data)

        # Build feature name mapping
        numerical_cols = ['person_age', 'person_income', 'person_emp_length',
                         'loan_amnt', 'loan_int_rate', 'loan_percent_income',
                         'cb_person_cred_hist_length']

        feature_names = numerical_cols.copy()

        # Get categorical feature names from one-hot encoder
        cat_features = preprocessor.named_transformers_['cat']
        if hasattr(cat_features.named_steps['onehot'], 'get_feature_names_out'):
            cat_feature_names = cat_features.named_steps['onehot'].get_feature_names_out()
            feature_names.extend(cat_feature_names)

        # Create SHAP explainer
        explainer = shap.TreeExplainer(model.named_steps['classifier'])
        shap_values = explainer.shap_values(preprocessed_data)

        # For binary classification, use values for class 1 (default risk)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        # Get SHAP values for the first sample
        if len(shap_values.shape) > 1:
            sample_shap_values = shap_values[0]
        else:
            sample_shap_values = shap_values

        sample_shap_values = np.atleast_1d(sample_shap_values).flatten()

        # Get the preprocessed feature values to check which categorical features are active
        if hasattr(preprocessed_data, 'toarray'):
            preprocessed_array = preprocessed_data.toarray()[0]
        else:
            preprocessed_array = preprocessed_data[0] if len(preprocessed_data.shape) > 1 else preprocessed_data

        original_values = input_data.iloc[0]

        # Readable name mappings
        numerical_readable = {
            'person_age': 'Age',
            'person_income': 'Income',
            'person_emp_length': 'Employment Length',
            'loan_amnt': 'Loan Amount',
            'loan_int_rate': 'Interest Rate',
            'loan_percent_income': 'Loan/Income Ratio',
            'cb_person_cred_hist_length': 'Credit History Length'
        }

        categorical_readable = {
            'RENT': 'Renting home',
            'OWN': 'Owning home',
            'MORTGAGE': 'Home with mortgage',
            'OTHER': 'Other housing',
            'DEBTCONSOLIDATION': 'Debt consolidation loan',
            'EDUCATION': 'Education loan',
            'HOMEIMPROVEMENT': 'Home improvement loan',
            'MEDICAL': 'Medical loan',
            'PERSONAL': 'Personal loan',
            'VENTURE': 'Business venture loan',
            'A': 'Grade A loan',
            'B': 'Grade B loan',
            'C': 'Grade C loan',
            'D': 'Grade D loan',
            'E': 'Grade E loan',
            'F': 'Grade F loan',
            'G': 'Grade G loan',
            'N': 'No default history',
            'Y': 'Previous default'
        }

        # Collect all valid features with their SHAP values
        candidates = []

        for idx in range(len(sample_shap_values)):
            if idx >= len(feature_names):
                continue

            feature_name = feature_names[idx]
            shap_value = sample_shap_values[idx]

            # Skip features with negligible impact
            if abs(shap_value) < 0.01:
                continue

            # Handle numerical features (first 7 features)
            if idx < len(numerical_cols):
                orig_feature = numerical_cols[idx]
                readable_name = numerical_readable.get(orig_feature, orig_feature.replace('_', ' ').title())
                value = original_values[orig_feature]

                if 'income' in orig_feature or 'amnt' in orig_feature:
                    feature_value_str = f" ${value:,.0f}"
                elif 'rate' in orig_feature:
                    feature_value_str = f" {value:.1f}%"
                elif 'percent' in orig_feature:
                    feature_value_str = f" {value:.1%}"
                elif 'age' in orig_feature:
                    feature_value_str = f" {int(value)}"
                elif 'length' in orig_feature:
                    feature_value_str = f" {value:.0f} years"
                else:
                    feature_value_str = f"{value}"

                impact = float(shap_value)

                candidates.append({
                    'abs_impact': abs(impact),
                    'text': f"{readable_name}: {feature_value_str}",
                    'is_numerical': True
                })

            # Handle one-hot encoded categorical features - ONLY if they're active (value = 1)
            elif feature_name.startswith('x') and '_' in feature_name:
                # Check if this categorical feature is active in the preprocessed data
                if idx < len(preprocessed_array) and preprocessed_array[idx] > 0.5:
                    parts = feature_name.split('_', 1)
                    if len(parts) == 2:
                        category_value = parts[1]
                        readable_name = categorical_readable.get(category_value,
                                                                category_value.replace('_', ' ').title())

                        impact = float(shap_value)

                        candidates.append({
                            'abs_impact': abs(impact),
                            'text': f"{readable_name}",
                            'is_numerical': False
                        })

        # Sort by: numerical features first, then by absolute impact
        candidates.sort(key=lambda x: (-x['is_numerical'], -x['abs_impact']))

        # Return top 2 explanations
        explanations = [c['text'] for c in candidates[:2]]
        return "; ".join(explanations) if explanations else "Standard risk assessment"

    except Exception as e:
        return f"Risk assessment (explanation unavailable)"

def predict_loan_status(input_data: LoanApplication | dict | pd.DataFrame, include_explanation: bool = False):
    """
    Predict loan status for a single input or batch.
    input_data: LoanApplication, dict or pd.DataFrame
    include_explanation: If True, returns explanation along with prediction
    """
    model = load_model()

    if isinstance(input_data, LoanApplication):
        input_data = input_data.model_dump()

    if isinstance(input_data, dict):
        input_data = pd.DataFrame([input_data])

    # Ensure consistency of derived features
    if 'loan_amnt' in input_data.columns and 'person_income' in input_data.columns:
        input_data['loan_percent_income'] = input_data['loan_amnt'] / input_data['person_income']

    # Ensure columns match training data (order doesn't matter for ColumnTransformer usually, but good practice)
    # The model pipeline handles preprocessing

    prediction = model.predict(input_data)
    probability = model.predict_proba(input_data)[:, 1]

    if include_explanation:
        explanation = explain_prediction(input_data, model)
        return prediction, probability, explanation

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
        'loan_amnt': 1000000000000000,
        'loan_int_rate': 10.0,
        'cb_person_default_on_file': 'N',
        'cb_person_cred_hist_length': 3
    }

    print("Running inference on sample input:")
    print(sample_input)

    pred, prob, explanation = predict_loan_status(sample_input, include_explanation=True)
    print(f"\nPrediction: {pred[0]} (0=Non-Default, 1=Default)")
    print(f"Probability of Default: {prob[0]:.4f}")
    print(f"Explanation: {explanation}")