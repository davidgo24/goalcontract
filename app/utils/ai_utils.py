import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in your environment variables.")
logging.info(f"OpenAI API key loaded (first 5 chars): {OPENAI_API_KEY[:5]}")

client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4o"

def generate_openai_message(prompt: str) -> str:
    full_prompt = (
        f"{prompt} Keep it between 30 to 40 words. Avoid repeating greetings or overly generic phrases."
    )
    logging.info(f"Generating response for prompt: {prompt[:80]}...")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            stream=False
        )
        message = response.choices[0].message.content
        logging.info("OpenAI response successfully received.")
        return message
    except Exception as e:
        logging.error(f"OpenAI generation failed: {e}", exc_info=True)
        return "Oops, something went wrong generating your message."
def test_openai_generation():
    logging.info("Running test_openai_generation...")
    test_prompt = (
        "Write a short, encouraging motivational quote for someone who is working towards a goal. "
        "Feel free to start with words from Kobe Bryant or other inspirational figures."
    )
    message = generate_openai_message(test_prompt)
    print(f"\n 🎯 OpenAI Response:\n{message}\n")

if __name__ == "__main__":
    test_openai_generation()