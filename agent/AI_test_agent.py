import os
import re
import sys
import tempfile
import subprocess
from datetime import datetime
from ipaddress import summarize_address_range

from openai import OpenAI
from fastapi import FastAPI
from typing import Optional


class AITestAgent:
    def __init__(self, app: FastAPI, api_key: str):
        self.app = app
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)
        self.schema = self.load_openapi_schema()
        self.app_path = ""
        self.generated_test_code = ""
        self.tests_file_path = ""
        self.start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def load_openapi_schema(self):
        print("📦 Loading OpenAPI schema...")
        return self.app.openapi()

    def read_app_source_code(self, path: str) -> str:
        print(f"📄 Reading FastAPI app from {path}...")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"File {path} not found.")
            sys.exit(1)

    def generate_tests(self, app_path: str, model: str = "z-ai/glm-4.5-air:free", temperature: float = 0.3):
        content = self.read_app_source_code(app_path)
        prompt = f"""
You are an expert Python test engineer.

Generate Pytest functions for testing all endpoints of a FastAPI app:

{content}

{self.schema}

Use realistic test data and assert status codes. Use the requests library.
Also cover performance, filtering and edge test cases. Make sure to clear database after each test run.
My app is in package {self.app_path}.
"""
        print("🤖 Generating tests...")
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You generate Python pytest test functions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            generated = response.choices[0].message.content
        except Exception as e:
            print(f"AI encountered an error during test generating: {e}")
            sys.exit(1)
        match = re.search(r"```(?:python)?\n(.*?)```", generated, re.DOTALL)
        self.generated_test_code = match.group(1) if match else generated
        print(f"✅ Generated {self.generated_test_code.count('def test')} tests.")

    def save_to_temp_file(self):
        print("💾 Saving tests to a temporary file...")
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
            temp_file.write(self.generated_test_code)
            self.tests_file_path = temp_file.name
        print(f"📂 Temp file path: {self.tests_file_path}")

    def save_to_permanent_file(self, directory: str = "tests", filename: str = f"test_generated_api_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.py"):
        print("💾 Saving tests to a file...")
        os.makedirs(directory, exist_ok=True)
        full_path = os.path.join(directory, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(self.generated_test_code)
        print(f"📁 Saved permanent test file to: {full_path}")
        self.tests_file_path = full_path

    def run_pytest(self, file_path: str) -> subprocess.CompletedProcess:
        print(f"🚀 Running tests...")
        return subprocess.run(
            [sys.executable, "-m", "pytest", file_path, "--tb=short", "-q"],
            capture_output=True,
            text=True
        )

    def summarize_results(self, result: subprocess.CompletedProcess):
        summary_match = re.search(r"(?P<failed>\d+)\s+failed,\s+(?P<passed>\d+)\s+passed", result.stdout)
        if not summary_match:
            summary_match = re.search(r"(?P<passed>\d+)\s+passed", result.stdout)

        if summary_match:
            passed = int(summary_match.group("passed"))
            failed = int(summary_match.group("failed")) if "failed" in summary_match.groupdict() else 0
            print(f"📊 Results: {passed} passed, {failed} failed")
        else:
            print("📊 Could not parse test result summary.")

    def log_test_results(self, result: subprocess.CompletedProcess, log_file: str = "logs/test_results.log"):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== Test Run: {timestamp} ===\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
            f.write("\n=============================\n")
        print(f"📝 Test results saved to {log_file}")

    def analyze_results_with_ai(self, result: subprocess.CompletedProcess, path: str) -> Optional[str]:
        print("🔎 Analyzing test results with AI...")
        new_prompt = (
            f"Analyze the following pytest output and suggest what issues may exist in the API implementation. "
            f"Suggest improvements for the API: {self.read_app_source_code(path)}. Structure your answer as bullet points.\n\n"
            f"{result.stdout}"
        )
        try:
            response = self.client.chat.completions.create(
                model="z-ai/glm-4.5-air:free",
                messages=[
                    {"role": "system", "content": "You are a Python test engineer."},
                    {"role": "user", "content": new_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error while analyzing test results: {e}"

    def save_ai_analysis(self, response_message: str, analysis_file: str = f"analysis/api_analysis_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log"):
        os.makedirs(os.path.dirname(analysis_file), exist_ok=True)
        with open(analysis_file, "a", encoding="utf-8") as f:
            f.write(response_message)
        print(f"📝 AI analysis saved to {analysis_file}")

    def clean_up(self):
        if self.tests_file_path and os.path.exists(self.tests_file_path):
            os.remove(self.tests_file_path)
            print("🧹 Temp file cleaned up.")

    def run_full_test_cycle(
        self,
        app_path: str,
        permanent_save: bool = False,
        log_file: str = f"logs/test_results_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log"
    ):
        self.app_path = app_path
        self.generate_tests(app_path)

        if permanent_save:
            self.save_to_permanent_file()
        else:
            self.save_to_temp_file()

        result = self.run_pytest(self.tests_file_path)

        self.summarize_results(result)

        self.log_test_results(result, log_file)

        analysis = self.analyze_results_with_ai(result, app_path)
        if analysis:
            print("🧠 AI Analysis:")
            print(analysis)
            self.save_ai_analysis(analysis)

        if not permanent_save:
            self.clean_up()