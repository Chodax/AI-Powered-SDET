from api.app import app
from agent import AI_test_agent
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")

test_generator = AI_test_agent.AITestAgent(app, API_KEY)
test_generator.run_full_test_cycle(
    app_path="api/app.py",
    permanent_save=True
)