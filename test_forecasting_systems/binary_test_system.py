import asyncio
import datetime
import json
import os
import re
import dotenv
import csv

from openai import AsyncOpenAI
import numpy as np


from reasoning_prompts import (
    FERMI_METHOD_PROMPT, 
    NAIVE_DIALECTIC_PROMPT, 
    PROPOSE_EVALUATE_SELECT_PROMPT, 
    BAYESIAN_REASONING_PROMPT, 
    ANTI_BIAS_PROMPT, 
    TIPPING_PROMPT, 
    SIMULATED_DIALOGUE_PROMPT, 
    BACKWARD_REASONING_PROMPT
)

dotenv.load_dotenv()
# METACULUS_TOKEN = os.getenv("METACULUS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

BINARY_REASONING_PROMPTS = [
    ("FERMI_METHOD", FERMI_METHOD_PROMPT),
    ("NAIVE_DIALECTIC", NAIVE_DIALECTIC_PROMPT),
    ("PROPOSE_EVALUATE_SELECT", PROPOSE_EVALUATE_SELECT_PROMPT),
    ("BAYESIAN_REASONING", BAYESIAN_REASONING_PROMPT),
    ("ANTI_BIAS", ANTI_BIAS_PROMPT),
    ("TIPPING", TIPPING_PROMPT),
    ("SIMULATED_DIALOGUE", SIMULATED_DIALOGUE_PROMPT),
    ("BACKWARD_REASONING", BACKWARD_REASONING_PROMPT)
]

BINARY_PROMPT_TEMPLATE = """
Question:
{title}

Question background:
{background}

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
{resolution_criteria}

{fine_print}

{reasoning_prompt}

The last thing you write is your final answer as: "Probability: ZZ%", 0-100
"""

client = AsyncOpenAI(
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
        max_retries=2,
    )

CONCURRENT_REQUESTS_LIMIT = 8
llm_rate_limiter = asyncio.Semaphore(CONCURRENT_REQUESTS_LIMIT)


async def call_llm(prompt: str, model: str = "gpt-4o", temperature: float = 0.3) -> str:
    """
    Makes a streaming completion request to OpenAI's API with concurrent request limiting.
    """
    async with llm_rate_limiter:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=False,
        )
        answer = response.choices[0].message.content
        if answer is None:
            raise ValueError("No answer returned from LLM")
        return answer
    
def extract_percentage_and_covert_to_decimal_from_response(
    forecast_text: str,
) -> float:
    matches = re.findall(r"(\d+)%", forecast_text)
    if matches:
        # Return the last number found before a '%'
        number = int(matches[-1])
        number = min(99, max(1, number))  # clamp the number between 1 and 99
        return number/ 100.0 # Convert to decimal
    else:
        raise ValueError(f"Could not extract prediction from response: {forecast_text}")

async def run_reasoning_method(question_details: dict, reasoning_name: str, reasoning_prompt: str):
    filled_prompt = BINARY_PROMPT_TEMPLATE.format(
        title=question_details["title"],
        background=question_details["description"],
        resolution_criteria=question_details["resolution_criteria"],
        fine_print=question_details["fine_print"],
        reasoning_prompt=reasoning_prompt
    )
    response = await call_llm(filled_prompt)
    probability = extract_percentage_and_covert_to_decimal_from_response(response)
    return reasoning_name, probability

async def process_binary_question(question_details: dict):
    resolution = question_details["resolution"].lower().strip()
    ground_truth = 1 if resolution == "yes" else 0


    results = await asyncio.gather(
        *[run_reasoning_method(question_details, name, prompt) for name, prompt in BINARY_REASONING_PROMPTS]
    )
    individual_forecasts = {name: prob for name, prob in results}
    individual_briers = {name: (prob - ground_truth)**2 for name, prob in results}
    
    ensemble_forecast = np.mean(list(individual_forecasts.values()))
    ensemble_brier = (ensemble_forecast - ground_truth)**2
    
    return {
        "question_id": question_details["id"],
        "title": question_details["title"],
        "resolution": question_details["resolution"],
        "ground_truth": ground_truth,
        "individual_forecasts": individual_forecasts,
        "individual_brier_scores": individual_briers,
        "ensemble_forecast": ensemble_forecast,
        "ensemble_brier": ensemble_brier
    }


async def binary_main():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    FILE = "q4-2024_binary_resolved_metaculus_questions.json"
    
    with open(FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    questions = [
        q for q in questions
        if q["resolution"].lower().strip() in ["yes", "no"] #to remove ambigious resolved questions
    ]

    all_results = []
    for i, question_details in enumerate(questions):
        print(f"Processing Question {i+1} / {len(questions)}: {question_details['title']}")
        result = await process_binary_question(question_details)
        all_results.append(result)

        # Save partial progress after each question (safety)
        with open(f"binary_experiment_results_{timestamp}.json", "w") as f:
            json.dump(all_results, f, indent=2)

        print(f"\nFinished Question {i+1}: '{result['title']}'")
        for name, _ in BINARY_REASONING_PROMPTS:
            brier = result["individual_brier_scores"][name]
            print(f" - {name}: Brier = {brier:.4f}")
        print(f"Ensemble Brier: {result['ensemble_brier']:.4f}")
        print("-" * 40)

    print("Saved experiment results as json.")

    brier_sums = {name: 0.0 for name, _ in BINARY_REASONING_PROMPTS}
    ensemble_brier_sum = 0.0
    N = len(all_results)

    for result in all_results:
        for name, _ in BINARY_REASONING_PROMPTS:
            brier_sums[name] += result["individual_brier_scores"][name]
        ensemble_brier_sum += result["ensemble_brier"]

    mean_brier_scores = {name: brier_sums[name] / N for name in brier_sums}
    mean_ensemble_brier = ensemble_brier_sum / N

    print("\nMean Brier Scores (ranked):")
    sorted_scores = sorted(mean_brier_scores.items(), key=lambda x: x[1])

    for rank, (name, score) in enumerate(sorted_scores, 1):
        print(f"{rank}. {name}: {score:.4f}")

    print(f"\nEnsemble Mean Brier: {mean_ensemble_brier:.4f}")
        
    with open(f"binary_experiment_results_{timestamp}.csv", "w", newline="") as csvfile:
        fieldnames = [
            "question_id", "title", "resolution", "ground_truth",
            "ensemble_forecast", "ensemble_brier"
        ] + [
            f"{name}_forecast" for name, _ in BINARY_REASONING_PROMPTS
        ] + [
            f"{name}_brier" for name, _ in BINARY_REASONING_PROMPTS
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in all_results:
            row = {
                "question_id": result["question_id"],
                "title": result["title"],
                "resolution": result["resolution"],
                "ground_truth": result["ground_truth"],
                "ensemble_forecast": result["ensemble_forecast"],
                "ensemble_brier": result["ensemble_brier"],
            }
            for name, _ in BINARY_REASONING_PROMPTS:
                row[f"{name}_forecast"] = result["individual_forecasts"][name]
                row[f"{name}_brier"] = result["individual_brier_scores"][name]
            writer.writerow(row)

if __name__ == "__main__":
    asyncio.run(binary_main())
