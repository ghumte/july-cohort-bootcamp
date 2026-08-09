import os
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# Read keys without displaying the actual secrets
openai_key = os.getenv("OPENAI_API_KEY")
langsmith_key = os.getenv("LANGSMITH_API_KEY")

print("OpenAI API key loaded:", bool(openai_key))
print("LangSmith API key loaded:", bool(langsmith_key))
print("LangSmith tracing:", os.getenv("LANGSMITH_TRACING"))