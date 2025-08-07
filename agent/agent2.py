import re
import subprocess
import sys
import tempfile

from agents import Agent, Runner

import asyncio

from dotenv import load_dotenv
load_dotenv()

tests_file_path = ""
app_path = "api/app.py"

def run_tests(file_path: str) -> str:
    """Runs tests"""
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", file_path, "--tb=short", "-q"],
            capture_output=True,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        return f"Error running run_tool: {str(e)}"

def summarize_results(result: subprocess.CompletedProcess):
    """Summarizes test results if run using subprocess."""
    summary_match = re.search(r"(?P<failed>\d+)\s+failed,\s+(?P<passed>\d+)\s+passed", result.stdout)
    if not summary_match:
        summary_match = re.search(r"(?P<passed>\d+)\s+passed", result.stdout)

    if summary_match:
        passed = int(summary_match.group("passed"))
        failed = int(summary_match.group("failed")) if "failed" in summary_match.groupdict() else 0
        print(f"📊 Results: {passed} passed, {failed} failed")
    else:
        print("📊 Could not parse test result summary.")

generation_agent = Agent(
    name="Test Case Generator",
    handoff_description="Agent that generates test cases using AI based on API definitions.",
    instructions=(
        "You are responsible for generating pytest-compatible test cases based on OpenAPI specifications."
        "Use AI capabilities to create tests for all endpoints, covering positive and negative scenarios."
    ),
)

execution_agent = Agent(
    name="Test Executor",
    handoff_description="Executes generated test code and summarizes results.",
    instructions=(
        "You execute dynamically generated test code using pytest locally."
        "Capture and return summary of pass/fail results."
    )
)

analysis_agent = Agent(
    name="Analyzer",
    handoff_description="Analyzes API and results of tests run on API.",
    instructions=(
        "You analyze API and results of tests run for that API."
        "Give suggestions on improving API"
    ),
)

triage_agent = Agent(
    name="API Test Orchestrator",
    instructions="Determine which task to run: test generation, test execution or analysis.",
    handoffs=[generation_agent, execution_agent, analysis_agent]
)


def read_app_source_code(path: str) -> str:
    print(f"📄 Reading FastAPI app from {path}...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {path} not found.")
        sys.exit(1)

async def main():
    api_code = read_app_source_code("../api/app.py")

    result = await Runner.run(triage_agent, f"Generate pytest test cases for all endpoints in this OpenAPI spec {api_code}."
                                            f"My app is in package {app_path}. Make sure all code is in one python file."
                                            f"Use realistic test data and assert status codes. Use the requests library. "
                                            f"Assume we are using `TestClient` from `fastapi.testclient`. Also cover"
                                            f"performance, filtering and edge test cases."
                                            f"Make sure to clear database after each test run")

    match = re.search(r"```(?:python)?\n(.*?)```", result.final_output, re.DOTALL)
    generated_test_code = match.group(1) if match else result.final_output
    print(f"✅ Generated {generated_test_code.count('def test')} tests.")

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(generated_test_code)
        global tests_file_path
        tests_file_path = temp_file.name

    await asyncio.sleep(20)

    result = await Runner.run(triage_agent, f"Execute python tests: {tests_file_path}. Structure answer in"
                                            f"format 'executed: number of executed tests\npassed: number of passed"
                                            f"\nfailed: number of failed tests'. After that write failures."
                                            f"specifying how many tests were executed, how many passed and how many"
                                            f"failed. If you were unable to run tests write 0 in executed, passed and failed")

    matches = re.findall(r'\b(executed|passed|failed):\s*(\d+)', result.final_output)
    result_nums = {key: int(value) for key, value in matches}

    if result_nums['executed'] == 0 and result_nums['passed'] == 0 and result_nums['failed'] == 0:
        test_summary = run_tests(tests_file_path)
        summarize_results(test_summary)
    else:
        print(f"📊 Results: {result_nums['passed']} passed, {result_nums['failed']} failed")
        test_summary = result.final_output


    await asyncio.sleep(20)
    prompt = (
        f"Analyze the following API test results with the goal of identifying weaknesses or inefficiencies"
        f"in the API design, behavior, performance, or robustness. API: {api_code}, Tests: {generated_test_code}, "
        f"Results: {test_summary}. Based on the failures, response patterns, and edge cases, provide concrete and"
        f"actionable suggestions to improve the API itself — such as enhancing response handling, improving error"
        f"messages, refining endpoint structure, handling edge cases more gracefully, or optimizing performance."
        f"Structure your answer in short and consise bullet points."
    )

    result = await Runner.run(triage_agent, prompt)
    print("🧠 AI Analysis:")
    print(result.final_output)



if __name__ == "__main__":
    asyncio.run(main())
