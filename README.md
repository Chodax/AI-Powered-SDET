# 🧪 AI-Powered Test Agent for FastAPI

This project is an **AI-powered automation tool** that:
- Generates **pytest** test cases for your FastAPI app using an LLM
- Runs the tests
- Logs test results
- Analyzes failures using AI
- Gives suggestion for improvements

---

## 📁 Project Structure

```
AI-Powered-SDET/
├── agent/
│   └── ai_test_agent.py       # Main AI test agent logic
├── api/
│   └── app.py                 # Your FastAPI app
├── tests/
│   └── test_generated_*.py    # Saved generated tests
├── logs/
│   └── test_results.log       # Test run logs
├── demo.py                    # Example usage
└── README.md
```

---

## ⚙️ Setup Instructions

### ✅ 1. Clone the Repository

```bash
git clone https://github.com/yourname/AI-Powered-SDET.git
cd AI-Powered-SDET
```

### ✅ 2. Create and activate virtual environment

```bash
python -m venv venv
.\venv\Scripts\activate
```

### ✅ 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### ✅ 4. Get an LLM API Key and set it up
Create a .env file in the root of the project and add your API key:

```.env
API_KEY="your_api_key"
```

### ✅ 5. Run demo.py file