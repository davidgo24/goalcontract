import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Configure logging for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv() # Load environment variables from .env file

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    logging.error("GOOGLE_API_KEY environment variable not set in .env file.")
    exit(1)

try:
    genai.configure(api_key=GEMINI_API_KEY)
    logging.info("Gemini API configured successfully.")
except Exception as e:
    logging.error(f"Failed to configure Gemini API. Please check your GOOGLE_API_KEY. Error: {e}")
    exit(1)

async def main():
    logging.info("Starting standalone Gemini API test...")
    test_prompt = "Tell me a short, encouraging quote suitable for a daily motivation app. Keep it concise."

    try:
        logging.info("Initializing GenerativeModel with 'models/gemini-2.5-flash-lite'.")
        model = genai.GenerativeModel('models/gemini-2.5-flash-lite') # Keep your chosen model name

        logging.info("Calling model.generate_content_async(test_prompt)... Expecting a response soon.")
        response = await model.generate_content_async(test_prompt)

        if response and response.text:
            logging.info("SUCCESS: Gemini API call returned a response!")
            logging.info(f"Generated text: {response.text[:200]}...") # Print first 200 chars
        else:
            logging.warning("WARNING: Gemini API call returned an empty or invalid response.")
            logging.warning(f"Full response object: {response}")

    except Exception as e:
        logging.error(f"FAILURE: An error occurred during Gemini content generation: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())