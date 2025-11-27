# uses machine learning model to produce a credit score with evidence
from src.models.ml_model import LoanApplication
from src.models.session import EvaluationEvidence
from src.ml.infer import predict_loan_status
import asyncio

async def ml_evaluate_loan(loan_application: LoanApplication) -> EvaluationEvidence:
    if not loan_application:
        return EvaluationEvidence(
            score=0,
            description="No loan application data provided for ML evaluation.",
            citation="",
            source="Machine Learning Model"
        )

    # Run inference in a separate thread to avoid blocking
    try:
        prediction, probability = await asyncio.to_thread(predict_loan_status, loan_application)
        
        # Probability is prob of Default (1).
        # We want a credit score where higher is better.
        # Score = (1 - prob_default) * 100
        prob_default = probability[0]
        score = int((1 - prob_default) * 100)
        
        is_default_pred = prediction[0] > 0.5
        status_str = "High Risk" if is_default_pred else "Low Risk"
        
        return EvaluationEvidence(
            score=score,
            description=status_str,
            citation="",
            source="Machine Learning Model"
        )
    except Exception as e:
        return EvaluationEvidence(
            score=0,
            description=f"ML Inference Failed: {str(e)}",
            citation="",
            source="Machine Learning Model"
        )