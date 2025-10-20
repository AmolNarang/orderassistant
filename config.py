import json

with open("appsettings.json", "r") as json_file:
    env_variables = json.load(json_file)

MODEL_NAME = env_variables.get("modelname")
API_KEY = env_variables.get("googleapi")
langsmith_key = env_variables.get("langsmithkey")




# Google API Key
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "your-api-key-here")

# Database
DATABASE_URL = "sqlite:///./orders.db"

# # LangSmith (optional)
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
# os.environ["LANGCHAIN_PROJECT"] = "simple-order-agent"