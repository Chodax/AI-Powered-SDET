import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from api.app import app, tasks_db, TaskPriority, StatusOfTask

@pytest.fixture(scope="function")
def client():
    """Create a test client and clear the database before each test."""
    with TestClient(app) as c:
        tasks_db.clear()
        yield c

@pytest.fixture
def sample_task_data():
    """Return sample task data for testing."""
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": TaskPriority.MEDIUM,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }

@pytest.fixture
def sample_task(client, sample_task_data):
    """Create and return a sample task."""
    response = client.post("/tasks", json=sample_task_data)
    return response.json()

# Test for POST /tasks
def test_create_task(client, sample_task_data):
    """Test creating a new task."""
    response = client.post("/tasks", json=sample_task_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_task_data["title"]
    assert data["description"] == sample_task_data["description"]
    assert data["priority"] == sample_task_data["priority"]
    assert data["status"] == StatusOfTask.PENDING  # Default status
    assert "task_id" in data
    assert datetime.fromisoformat(data["due_date"]) == datetime.fromisoformat(sample_task_data["due_date"])

def test_create_task_missing_required_fields(client):
    """Test creating a task with missing required fields."""
    task_data = {
        "title": "Test Task"
        # Missing priority and due_date
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_create_task_invalid_priority(client):
    """Test creating a task with invalid priority."""
    task_data = {
        "title": "Test Task",
        "priority": 4,  # Invalid priority
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_create_task_past_due_date(client):
    """Test creating a task with a past due date."""
    task_data = {
        "title": "Test Task",
        "priority": TaskPriority.MEDIUM,
        "due_date": (datetime.now() - timedelta(days=1)).isoformat()  # Past date
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_create_task_empty_title(client):
    """Test creating a task with an empty title."""
    task_data = {
        "title": "",  # Empty title
        "priority": TaskPriority.MEDIUM,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_create_task_long_title(client):
    """Test creating a task with a title that's too long."""
    task_data = {
        "title": "a" * 101,  # Title too long
        "priority": TaskPriority.MEDIUM,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_create_task_long_description(client):
    """Test creating a task with a description that's too long."""
    task_data = {
        "title": "Test Task",
        "description": "a" * 501,  # Description too long
        "priority": TaskPriority.MEDIUM,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

# Test for GET /tasks
def test_list_tasks(client, sample_task):
    """Test listing all tasks."""
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["task_id"] == sample_task["task_id"]

def test_list_tasks_empty(client):
    """Test listing tasks when the database is empty."""
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_list_tasks_filter_by_status(client, sample_task_data):
    """Test listing tasks filtered by status."""
    # Create a completed task
    completed_task_data = sample_task_data.copy()
    response = client.post("/tasks", json=completed_task_data)
    completed_task = response.json()
    
    # Update the status to completed
    client.patch(f"/tasks/{completed_task['task_id']}/status", params={"status": StatusOfTask.COMPLETED})
    
    # List pending tasks
    response = client.get("/tasks", params={"status": StatusOfTask.PENDING})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == StatusOfTask.PENDING
    
    # List completed tasks
    response = client.get("/tasks", params={"status": StatusOfTask.COMPLETED})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == StatusOfTask.COMPLETED

def test_list_tasks_filter_by_priority(client, sample_task_data):
    """Test listing tasks filtered by priority."""
    # Create tasks with different priorities
    high_priority_task_data = sample_task_data.copy()
    high_priority_task_data["priority"] = TaskPriority.HIGH
    response = client.post("/tasks", json=high_priority_task_data)
    high_priority_task = response.json()
    
    low_priority_task_data = sample_task_data.copy()
    low_priority_task_data["priority"] = TaskPriority.LOW
    response = client.post("/tasks", json=low_priority_task_data)
    low_priority_task = response.json()
    
    # List high priority tasks
    response = client.get("/tasks", params={"priority": TaskPriority.HIGH})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["priority"] == TaskPriority.HIGH
    
    # List low priority tasks
    response = client.get("/tasks", params={"priority": TaskPriority.LOW})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["priority"] == TaskPriority.LOW
    
    # List medium priority tasks
    response = client.get("/tasks", params={"priority": TaskPriority.MEDIUM})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["priority"] == TaskPriority.MEDIUM

def test_list_tasks_filter_by_status_and_priority(client, sample_task_data):
    """Test listing tasks filtered by both status and priority."""
    # Create multiple tasks with different priorities and statuses
    tasks = []
    for priority in TaskPriority:
        for status in StatusOfTask:
            task_data = sample_task_data.copy()
            task_data["priority"] = priority
            response = client.post("/tasks", json=task_data)
            task = response.json()
            client.patch(f"/tasks/{task['task_id']}/status", params={"status": status})
            tasks.append(task)
    
    # Filter by specific status and priority
    response = client.get("/tasks", params={"status": StatusOfTask.COMPLETED, "priority": TaskPriority.HIGH})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == StatusOfTask.COMPLETED
    assert data[0]["priority"] == TaskPriority.HIGH

# Test for GET /tasks/{task_id}
def test_get_task(client, sample_task):
    """Test getting a specific task by ID."""
    task_id = sample_task["task_id"]
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["title"] == sample_task["title"]

def test_get_task_not_found(client):
    """Test getting a task with a non-existent ID."""
    task_id = uuid4()
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_get_task_invalid_id(client):
    """Test getting a task with an invalid ID format."""
    response = client.get("/tasks/invalid-id")
    assert response.status_code == 422

# Test for PUT /tasks/{task_id}
def test_update_task(client, sample_task_data):
    """Test updating a task."""
    # Create a task
    response = client.post("/tasks", json=sample_task_data)
    task = response.json()
    
    # Update the task
    update_data = {
        "title": "Updated Task",
        "description": "Updated description",
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=14)).isoformat()
    }
    response = client.put(f"/tasks/{task['task_id']}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]
    assert data["priority"] == update_data["priority"]
    assert datetime.fromisoformat(data["due_date"]) == datetime.fromisoformat(update_data["due_date"])
    # Status should remain unchanged
    assert data["status"] == StatusOfTask.PENDING

def test_update_task_partial(client, sample_task_data):
    """Test partially updating a task."""
    # Create a task
    response = client.post("/tasks", json=sample_task_data)
    task = response.json()
    
    # Update only the title
    update_data = {"title": "Updated Task"}
    response = client.put(f"/tasks/{task['task_id']}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    # Other fields should remain unchanged
    assert data["description"] == sample_task_data["description"]
    assert data["priority"] == sample_task_data["priority"]
    assert data["status"] == StatusOfTask.PENDING

def test_update_task_not_found(client, sample_task_data):
    """Test updating a non-existent task."""
    task_id = uuid4()
    update_data = {"title": "Updated Task"}
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_update_task_invalid_id(client, sample_task_data):
    """Test updating a task with an invalid ID format."""
    response = client.put("/tasks/invalid-id", json={"title": "Updated Task"})
    assert response.status_code == 422

def test_update_task_invalid_data(client, sample_task_data):
    """Test updating a task with invalid data."""
    # Create a task
    response = client.post("/tasks", json=sample_task_data)
    task = response.json()
    
    # Update with invalid data
    update_data = {
        "title": "",  # Empty title
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=14)).isoformat()
    }
    response = client.put(f"/tasks/{task['task_id']}", json=update_data)
    assert response.status_code == 422

# Test for DELETE /tasks/{task_id}
def test_delete_task(client, sample_task):
    """Test deleting a task."""
    task_id = sample_task["task_id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Task deleted"
    
    # Verify the task is deleted
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404

def test_delete_task_not_found(client):
    """Test deleting a non-existent task."""
    task_id = uuid4()
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_delete_task_invalid_id(client):
    """Test deleting a task with an invalid ID format."""
    response = client.delete("/tasks/invalid-id")
    assert response.status_code == 422

# Test for PATCH /tasks/{task_id}/status
def test_update_status(client, sample_task):
    """Test updating the status of a task."""
    task_id = sample_task["task_id"]
    response = client.patch(f"/tasks/{task_id}/status", params={"status": StatusOfTask.COMPLETED})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == StatusOfTask.COMPLETED
    # Other fields should remain unchanged
    assert data["title"] == sample_task["title"]
    assert data["priority"] == sample_task["priority"]

def test_update_status_not_found(client):
    """Test updating the status of a non-existent task."""
    task_id = uuid4()
    response = client.patch(f"/tasks/{task_id}/status", params={"status": StatusOfTask.COMPLETED})
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_update_status_invalid_id(client):
    """Test updating the status with an invalid ID format."""
    response = client.patch("/tasks/invalid-id/status", params={"status": StatusOfTask.COMPLETED})
    assert response.status_code == 422

def test_update_status_invalid_status(client, sample_task):
    """Test updating the status with an invalid status value."""
    task_id = sample_task["task_id"]
    response = client.patch(f"/tasks/{task_id}/status", params={"status": 2})  # Invalid status
    assert response.status_code == 422

# Performance tests
def test_create_task_performance(client, sample_task_data):
    """Test performance of creating multiple tasks."""
    num_tasks = 100
    start_time = datetime.now()
    
    for _ in range(num_tasks):
        response = client.post("/tasks", json=sample_task_data)
        assert response.status_code == 200
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\nCreated {num_tasks} tasks in {duration:.2f} seconds")
    # Assert that it takes less than 5 seconds to create 100 tasks
    assert duration < 5

def test_list_tasks_performance(client, sample_task_data):
    """Test performance of listing tasks."""
    # Create 100 tasks
    num_tasks = 100
    for _ in range(num_tasks):
        response = client.post("/tasks", json=sample_task_data)
        assert response.status_code == 200
    
    # Test listing performance
    start_time = datetime.now()
    response = client.get("/tasks")
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    assert response.status_code == 200
    assert len(response.json()) == num_tasks
    print(f"\nListed {num_tasks} tasks in {duration:.4f} seconds")
    # Assert that it takes less than 1 second to list 100 tasks
    assert duration < 1

def test_list_tasks_filter_performance(client, sample_task_data):
    """Test performance of listing tasks with filters."""
    # Create 100 tasks with different priorities
    num_tasks = 100
    for i in range(num_tasks):
        task_data = sample_task_data.copy()
        task_data["priority"] = TaskPriority(i % 3 + 1)  # Cycle through priorities
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 200
    
    # Test filtering by priority performance
    start_time = datetime.now()
    response = client.get("/tasks", params={"priority": TaskPriority.HIGH})
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    assert response.status_code == 200
    print(f"\nFiltered {num_tasks} tasks by priority in {duration:.4f} seconds")
    # Assert that it takes less than 1 second to filter 100 tasks
    assert duration < 1
