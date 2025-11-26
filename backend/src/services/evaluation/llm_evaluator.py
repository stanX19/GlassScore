from src.models.evaluate import EvaluationRequest, EvaluationEvidence, UserProfile
import asyncio


from src.llm.rotating_llm import rotating_llm
from src.models.session import TextContent


async def llm_evaluate_loan(
	content: TextContent,
	other_evidence_tasks: list[asyncio.Task[EvaluationEvidence]] = None,
	objective: str = None
) -> list[EvaluationEvidence]:
	other_evidence_tasks = other_evidence_tasks or []
	
	# Wait for other evidence (e.g. ML score) to provide context
	other_evidence_list: list[EvaluationEvidence] = []
	if other_evidence_tasks:
		try:
			# We wait for the tasks, but we don't want to fail if they fail
			results = await asyncio.gather(*other_evidence_tasks, return_exceptions=True)
			for res in results:
				if isinstance(res, EvaluationEvidence):
					other_evidence_list.append(res)
				elif isinstance(res, list): # Handle list of evidence
					other_evidence_list.extend([item for item in res if isinstance(item, EvaluationEvidence)])
		except Exception as e:
			print(f"Error gathering other evidence: {e}")

	base_instruction = "You are a credit score evaluator for a bank. Your task is to analyze the following text from a loan applicant and evaluate their behavior."
	is_web_search = content.source.startswith("web_search")
	
	if objective:
		base_instruction = f"You are a risk analyst. Your task is to analyze the following text with this objective: {objective}"

	# Add context from other evidence (e.g. ML model)
	context_info = ""
	if other_evidence_list:
		context_info += "\n\nAdditional Context from other Evidence:\n"
		for ev in other_evidence_list:
			context_info += f"- Score: {ev.score}\n- Insight: {ev.description}\n"

	# Special instructions for web search results
	web_search_warning = ""
	if is_web_search:
		web_search_warning = """
	IMPORTANT: This text comes from web search results that have already been verified to match the applicant's identity.
	However, be CAUTIOUS:
	- Only cite information that is clearly relevant to credit risk
	- Positive professional information (employment, achievements) should score +2
	- Absence of negative information is NOT evidence (don't score it)
	- Only assign negative scores (-5, -10) if you find actual concerning behavior (gambling, fraud, legal issues, financial instability)
	- If the information is neutral or just biographical, return empty evidence list
	"""

	prompt = f"""
	{base_instruction}
	{context_info}
	{web_search_warning}
	
	Text to evaluate:
	"{content.text}"
	
	Analyze the text for behavioral signals and assign a score based on the following criteria:
	- GOOD: 2 (Verified with evidence, logical behavior, stable employment)
	- NORMAL: 0 (Neutral, standard behavior)
	- MINOR ISSUE: -5 (Slight concerns, illogical description, suspicious writings)
	- WARNING: -10 (Red flags, gambling, instability, high risk, major inconsistencies)
	
	Return a JSON object with the following field:
	- "evidence": A list of evidence items. Each item should have:
		- "score": The integer score assigned (2, 0, -5, or -10).
		- "citation": The exact excerpt from the text that supports this evaluation (quote it directly, not more than 10 words).
		- "description": A brief explanation of why this citation is concerning or noteworthy. Not more than 15 words.
	
	If there is no evidence of concerning or noteworthy behavior, return an empty list for "evidence".
	"""

	try:
		response = await rotating_llm.send_message_get_json(
			messages=prompt,
			temperature=0.3 # Low temperature for consistent scoring
		)
		if response["status"] == "ok" and "json" in response:
			data = response["json"]
			evidence_list = data.get("evidence", [])
			
			# Convert each evidence item to EvaluationEvidence object
			result = []
			for item in evidence_list:
				result.append(EvaluationEvidence(
					score=item.get("score", 0),
					description=item.get("description", "No description provided."),
					citation=item.get("citation", ""),
					source=content.source
				))
			return result
		else:
			return [EvaluationEvidence(
				score=0,
				description=f"Failed to evaluate text: {response.get('text', 'Unknown error')}",
				citation="",
				source=content.source
			)]
	except Exception as e:
		return [EvaluationEvidence(
			score=0,
			description=f"Error during LLM evaluation: {str(e)}",
			citation="",
			source=content.source
		)]

if __name__ == '__main__':
	async def main():
		# Test prompts list
		prompts: list[str] = [
			# "I am applying for a loan to renovate my kitchen. I have a stable job and savings.",
			# "I need this loan for my gambling debts and to pay off some urgent bills.",
			"""Tavily Search Results: {
  "content": "My name is Joemer Ramos! Im a software engineer by day and an aspiring tech influencer by night<br><br> I have two goals that Im trying to achieve<br><br> The first goal is to pique your interest enough to check out my profile<br><br> So yay, one down and welcome! The second is a little more challenging<br><br> I want to help people grow<br><br> Ive always loved self-improvement and feel like my perspective can inspire people to have a better life<br><br> I want to do my best to be an [...] # Joemer R.\nSoftware Engineer at Google\nNew York, New York, United States, US  \n500 connections, 1682 followers [...] ## Experience\n### Software Engineer  \nGoogle  \nSep 2021 - Present   \nNew York City Metropolitan Area  \nChrome for iOS\n\n### Content Creator  \nYouTube  \nJan 2023 - Present   \nNew York City Metropolitan Area  \nCreating YouTube videos about self improvement, productivity, and my life in tech",
  "url": "https://www.linkedin.com/in/joemerramos",
  "title": "Joemer R. - Software Engineer at Google | LinkedIn"
}
{
  "content": "# Hi, Im Joemer!\n\nIm an aspiring tech influencer and software engineer. By creating content and digital products, I hope that I could help inspire and educate people around the world. Join my newsletter for monthly progress updates!\n\n### 2920\n\n### Days of coding\n\n### 10,000+\n\n### Lines of code written\n\n### 1.5k\n\n### Followers\n\n### $0\n\n### Payments/Free Content\n\n## Documenting My Journey\n\n## 50+\n\n## hours of content [...] ### Youve explored my site this far. To thank you, heres advice to help you on your journey!\n\nFrom time to time, Ill also share thoughts on mental health and self improvement. But why? That doesnt have to do with coding! Heres the first of many valuable lessons, 10% of the battle is coding. 90% of software engineering is having the mental resilience to learn, grow, and adapt in the face of ambiguity, difficult tasks, and without a doubt, bugs that we somehow create. [...] Dive into my ever-growing collection of content! Stay tuned for more updates and adventures!\n\n### Whats my YouTube channel about?\n\nOn my channel, youll find a behind-the-scenes look into my life as a software engineer, tech content creator, and my coding journey! My goal for every video is to inspire and educate you by being authentic, sharing well-known coding practices, and showing my adaptive thought process as I code and debug.\n\n### Watch more videos",
  "url": "https://joemerramos.com/",
  "title": "Joemer Ramos - Blog About Life and Self Improvement"
}

"""
		]

		print(f"Starting verification...", flush=True)
		try:
			with open("verification_output.txt", "w") as f:
				for i, prompt_text in enumerate(prompts, 1):
					f.write(f"\n{'='*60}\n")
					f.write(f"Test Case {i}\n")
					f.write(f"{'='*60}\n")
					f.write(f"Testing with text: '{prompt_text}'\n\n")
					print(f"\nTest Case {i}: '{prompt_text}'", flush=True)

					# Create TextContent for this prompt
					content = TextContent(
						text=prompt_text,
						key=f"test_prompt_{i}.txt",
						source="user_upload"
					)

					# Evaluate the prompt
					evidence_list = await llm_evaluate_loan(content)

					# Display results
					if evidence_list:
						f.write(f"Found {len(evidence_list)} evidence item(s):\n")
						print(f"Found {len(evidence_list)} evidence item(s):", flush=True)
						for j, evidence in enumerate(evidence_list, 1):
							f.write(f"  Evidence {j}:\n")
							f.write(f"    Score: {evidence.score}\n")
							f.write(f"    Citation: {evidence.citation}\n")
							f.write(f"    Description: {evidence.description}\n")
							f.write(f"    Source: {evidence.source}\n")
							print(f"  Evidence {j}: Score={evidence.score}, Citation='{evidence.citation}', Description='{evidence.description}'", flush=True)
					else:
						f.write("No evidence found (empty list)\n")
						print("No evidence found (empty list)", flush=True)
		except Exception as e:
			print(f"Error: {e}", flush=True)
			import traceback
			traceback.print_exc()

	import sys
	if sys.platform.startswith("win"):
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	asyncio.run(main())