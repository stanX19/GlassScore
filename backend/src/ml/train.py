import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import os

# Set random seed for reproducibility
np.random.seed(42)

def train():
    print("Loading datasets...")
    base_dir = os.path.dirname(__file__)
    train_path = os.path.join(base_dir, 'data', 'train.csv')
    test_path = os.path.join(base_dir, 'data', 'test.csv')
    
    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)
    
    # Define features and target
    target = 'loan_status'
    X = df_train.drop(columns=['id', target])
    y = df_train[target]
    
    # Prepare test data (drop id if present, ensure columns match)
    X_test_submission = df_test.drop(columns=['id'], errors='ignore')
    
    # Identify categorical and numerical columns
    categorical_features = ['person_home_ownership', 'loan_intent', 'loan_grade', 'cb_person_default_on_file']
    numerical_features = ['person_age', 'person_income', 'person_emp_length', 'loan_amnt', 'loan_int_rate', 'loan_percent_income', 'cb_person_cred_hist_length']
    
    print("Preprocessing data...")
    # Create transformers
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    
    # Combine transformers
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ])
    
    # Create pipeline with a placeholder classifier
    pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                               ('classifier', RandomForestClassifier(random_state=42, n_jobs=-1))])
    
    # Split training data for validation
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Define hyperparameter search space
    param_dist = {
        'classifier__n_estimators': [100, 200, 300],
        'classifier__max_depth': [None, 10, 20, 30],
        'classifier__min_samples_split': [2, 5, 10],
        'classifier__min_samples_leaf': [1, 2, 4],
        'classifier__bootstrap': [True, False]
    }
    
    print("Starting AutoML (RandomizedSearchCV)...")
    # RandomizedSearchCV
    random_search = RandomizedSearchCV(
        pipeline, 
        param_distributions=param_dist, 
        n_iter=10, # Number of parameter settings that are sampled
        cv=3,      # 3-fold cross-validation
        verbose=2, 
        random_state=42, 
        n_jobs=-1,
        scoring='roc_auc'
    )
    
    random_search.fit(X_train, y_train)
    
    print(f"Best parameters found: {random_search.best_params_}")
    print(f"Best cross-validation AUC: {random_search.best_score_:.4f}")
    
    best_model = random_search.best_estimator_
    
    print("Evaluating best model on validation set...")
    y_pred = best_model.predict(X_val)
    y_prob = best_model.predict_proba(X_val)[:, 1]
    
    print(classification_report(y_val, y_pred))
    print(f"Validation ROC AUC Score: {roc_auc_score(y_val, y_prob):.4f}")
    
    # Save model
    print("Saving model...")
    model_path = os.path.join(base_dir, 'models/loan_model.joblib')
    joblib.dump(best_model, model_path)
    print(f"Model saved to {model_path}")
    
    # Generate predictions for test.csv
    print("Generating predictions for test.csv...")
    test_probs = best_model.predict_proba(X_test_submission)[:, 1]
    test_preds = best_model.predict(X_test_submission)
    
    # Create submission dataframe
    submission = pd.DataFrame({
        'id': df_test['id'],
        'loan_status_pred': test_preds,
        'loan_status_prob': test_probs
    })
    
    submission_path = os.path.join(base_dir, 'predictions.csv')
    submission.to_csv(submission_path, index=False)
    print(f"Predictions saved to {submission_path}")

if __name__ == '__main__':
    train()