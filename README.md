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

### ✅ 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### ✅ 3. Get an LLM API Key


### ✅ 4. Run demo.py file