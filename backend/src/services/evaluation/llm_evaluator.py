from src.models.evaluate import EvaluationRequest, EvaluationEvidence, UserProfile, LLMEvaluationParams
import asyncio


from src.llm.rotating_llm import rotating_llm
from src.models.session import TextContent


async def llm_evaluate_loan(
	params: LLMEvaluationParams,
	other_evidence_tasks: list[asyncio.Task[EvaluationEvidence]] = None
) -> EvaluationEvidence:
	other_evidence_tasks = other_evidence_tasks or []
	# We can wait for other evidence if needed, but for now we might just want to proceed with the text analysis
	# other_evidence: list[EvaluationEvidence] = await asyncio.gather(*other_evidence_tasks)

	prompt = f"""
	You are a credit score evaluator for a bank. Your task is to analyze the following text from a loan applicant and evaluate their behavior.
	
	Text to evaluate:
	"{params.text_content.text}"
	
	Analyze the text for behavioral signals and assign a score based on the following criteria:
	- NORMAL: 0 (Neutral, standard behavior)
	- MINOR ISSUE: -10 (Slight concerns, illogical description, suspicious writings)
	- WARNING: -20 (Red flags, gambling, instability, high risk, major inconsistencies)
	
	Return a JSON object with the following fields:
	- "score": The integer score assigned (10, 0, -10, or -20).
	- "description": A citation of specific parts of the text that leads to the conclusion. Not more than 15 words
	"""

	try:
		response = await rotating_llm.send_message_get_json(
			messages=prompt,
			temperature=0.1 # Low temperature for consistent scoring
		)
		
		if response["status"] == "ok" and "json" in response:
			data = response["json"]
			return EvaluationEvidence(
				score=data.get("score", 0),
				description=data.get("description", "No description provided."),
				source=params.text_content.source
			)
		else:
			return EvaluationEvidence(
				score=0,
				description=f"Failed to evaluate text: {response.get('text', 'Unknown error')}",
				source=params.text_content.source
			)
	except Exception as e:
		return EvaluationEvidence(
			score=0,
			description=f"Error during LLM evaluation: {str(e)}",
			source=params.text_content.source
		)

if __name__ == '__main__':
	async def main():
		# Test case 1: Gambling behavior (Should be WARNING -20)
		gambling_text = "I have a stable work and income. I have a family of two and I have 2 houses. I needed the loan because I need to pay for my fourth child's new car"
		params_gambling = LLMEvaluationParams(
			text_content=TextContent(
				text=gambling_text,
				key="gambling_note.txt",
				source="user_upload"
			)
		)

		# Test case 2: Responsible behavior (Should be GOOD 10)
		responsible_text = "I am applying for a loan to renovate my kitchen. I have a stable job and savings. I also have passive income through stocks and shares"
		params_responsible = LLMEvaluationParams(
			text_content=TextContent(
				text=responsible_text,
				key="renovation_plan.txt",
				source="user_upload"
			)
		)

		print(f"Starting verification...", flush=True)
		try:
			with open("verification_output.txt", "w") as f:
				f.write(f"Testing with text: '{gambling_text}'\n")
				print(f"Testing with text: '{gambling_text}'", flush=True)

				result_gambling = await llm_evaluate_loan(params_gambling)

				f.write(f"Result: Score={result_gambling.score}, Description='{result_gambling.description}'\n")
				print(f"Result: Score={result_gambling.score}, Description='{result_gambling.description}'", flush=True)



				f.write(f"\nTesting with text: '{responsible_text}'\n")
				print(f"\nTesting with text: '{responsible_text}'", flush=True)

				result_responsible = await llm_evaluate_loan(params_responsible)

				f.write(f"Result: Score={result_responsible.score}, Description='{result_responsible.description}'\n")
				print(f"Result: Score={result_responsible.score}, Description='{result_responsible.description}'",
					  flush=True)
		except Exception as e:
			print(f"Error: {e}", flush=True)
			import traceback
			traceback.print_exc()

	import sys
	if sys.platform.startswith("win"):
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	asyncio.run(main())