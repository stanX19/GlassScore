# uses machine learning model to produce a credit score with evidence
from src.models.evaluate import EvaluationRequest, EvaluationEvidence, UserProfile

async def ml_evaluate_loan(user_profile: UserProfile) -> EvaluationEvidence:
	# TODO: implement machine learning model
	return EvaluationEvidence(
		score=80,
		description="Good Credit Score",
		source="Machine Learning Model"
	)