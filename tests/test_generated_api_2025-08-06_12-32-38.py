import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from api.app import app, tasks_db, TaskPriority, StatusOfTask

# Setup for tests
@pytest.fixture(scope="function")
def client():
    """Create a test client and clear the database before each test"""
    with TestClient(app) as c:
        tasks_db.clear()
        yield c

# Test data
@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }

@pytest.fixture
def sample_task_id():
    """Sample task ID for testing"""
    return uuid4()

# Tests for POST /tasks
def test_create_task(client, sample_task_data):
    """Test creating a new task"""
    response = client.post("/tasks", json=sample_task_data)
    assert response.status_code == 200
    
    task = response.json()
    assert task["title"] == sample_task_data["title"]
    assert task["description"] == sample_task_data["description"]
    assert task["priority"] == sample_task_data["priority"]
    assert task["status"] == StatusOfTask.PENDING  # Default status
    assert "task_id" in task
    assert "due_date" in task

def test_create_task_missing_required_fields(client):
    """Test creating a task with missing required fields"""
    task_data = {
        "title": "Test Task"
        # Missing priority and due_date
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422  # Validation error

def test_create_task_invalid_priority(client):
    """Test creating a task with invalid priority"""
    task_data = {
        "title": "Test Task",
        "priority": 4,  # Invalid priority
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422  # Validation error

def test_create_task_past_due_date(client):
    """Test creating a task with past due date"""
    task_data = {
        "title": "Test Task",
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() - timedelta(days=1)).isoformat()  # Past date
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422  # Validation error

def test_create_task_long_title(client):
    """Test creating a task with a title that's too long"""
    long_title = "a" * 101  # Exceeds max length of 100
    task_data = {
        "title": long_title,
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422  # Validation error

def test_create_task_empty_title(client):
    """Test creating a task with an empty title"""
    task_data = {
        "title": "",  # Empty title
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422  # Validation error

def test_create_task_long_description(client):
    """Test creating a task with a description that's too long"""
    long_description = "a" * 501  # Exceeds max length of 500
    task_data = {
        "title": "Test Task",
        "description": long_description,
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422  # Validation error

# Tests for GET /tasks
def test_list_tasks_empty(client):
    """Test listing tasks when the database is empty"""
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []

def test_list_tasks_with_data(client, sample_task_data):
    """Test listing tasks when there are tasks in the database"""
    # Create a task
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    
    # List tasks
    response = client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == sample_task_data["title"]

def test_list_tasks_filter_by_status(client, sample_task_data):
    """Test listing tasks filtered by status"""
    # Create a task with PENDING status (default)
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    
    # Create another task with COMPLETED status
    completed_task_data = sample_task_data.copy()
    completed_task_data["status"] = StatusOfTask.COMPLETED
    create_response = client.post("/tasks", json=completed_task_data)
    assert create_response.status_code == 200
    
    # Filter by PENDING status
    response = client.get("/tasks?status=0")  # 0 is PENDING
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["status"] == StatusOfTask.PENDING
    
    # Filter by COMPLETED status
    response = client.get("/tasks?status=1")  # 1 is COMPLETED
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["status"] == StatusOfTask.COMPLETED

def test_list_tasks_filter_by_priority(client, sample_task_data):
    """Test listing tasks filtered by priority"""
    # Create a task with HIGH priority
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    
    # Create another task with LOW priority
    low_priority_task_data = sample_task_data.copy()
    low_priority_task_data["priority"] = TaskPriority.LOW
    create_response = client.post("/tasks", json=low_priority_task_data)
    assert create_response.status_code == 200
    
    # Filter by HIGH priority
    response = client.get("/tasks?priority=3")  # 3 is HIGH
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["priority"] == TaskPriority.HIGH
    
    # Filter by LOW priority
    response = client.get("/tasks?priority=1")  # 1 is LOW
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["priority"] == TaskPriority.LOW

def test_list_tasks_filter_by_status_and_priority(client, sample_task_data):
    """Test listing tasks filtered by both status and priority"""
    # Create multiple tasks with different combinations
    task_data = sample_task_data.copy()
    create_response = client.post("/tasks", json=task_data)
    assert create_response.status_code == 200
    
    task_data["priority"] = TaskPriority.LOW
    create_response = client.post("/tasks", json=task_data)
    assert create_response.status_code == 200
    
    task_data["status"] = StatusOfTask.COMPLETED
    create_response = client.post("/tasks", json=task_data)
    assert create_response.status_code == 200
    
    # Filter by both status and priority
    response = client.get("/tasks?status=0&priority=3")  # PENDING and HIGH
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["status"] == StatusOfTask.PENDING
    assert tasks[0]["priority"] == TaskPriority.HIGH

def test_list_tasks_invalid_status_filter(client):
    """Test listing tasks with an invalid status filter"""
    response = client.get("/tasks?status=2")  # Invalid status
    assert response.status_code == 422  # Validation error

def test_list_tasks_invalid_priority_filter(client):
    """Test listing tasks with an invalid priority filter"""
    response = client.get("/tasks?priority=4")  # Invalid priority
    assert response.status_code == 422  # Validation error

def test_list_tasks_performance(client):
    """Test performance of listing tasks with many entries"""
    # Create 100 tasks
    for i in range(100):
        task_data = sample_task_data.copy()
        task_data["title"] = f"Task {i}"
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 200
    
    # List all tasks and measure time
    start_time = datetime.now()
    response = client.get("/tasks")
    end_time = datetime.now()
    
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 100
    
    # Check that the response time is reasonable (less than 1 second)
    assert (end_time - start_time).total_seconds() < 1

# Tests for GET /tasks/{task_id}
def test_get_task(client, sample_task_data):
    """Test getting a specific task by ID"""
    # Create a task
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    task_id = create_response.json()["task_id"]
    
    # Get the task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    task = response.json()
    assert task["title"] == sample_task_data["title"]
    assert task["task_id"] == str(task_id)

def test_get_nonexistent_task(client):
    """Test getting a task that doesn't exist"""
    nonexistent_id = uuid4()
    response = client.get(f"/tasks/{nonexistent_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_get_task_invalid_id_format(client):
    """Test getting a task with an invalid ID format"""
    response = client.get("/tasks/invalid-id")
    assert response.status_code == 422  # Validation error

# Tests for PUT /tasks/{task_id}
def test_update_task(client, sample_task_data):
    """Test updating a task"""
    # Create a task
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    task_id = create_response.json()["task_id"]
    
    # Update the task
    update_data = {
        "title": "Updated Task",
        "description": "Updated description",
        "priority": TaskPriority.LOW,
        "status": StatusOfTask.COMPLETED,
        "due_date": (datetime.now() + timedelta(days=14)).isoformat()
    }
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    
    # Verify the update
    updated_task = response.json()
    assert updated_task["title"] == update_data["title"]
    assert updated_task["description"] == update_data["description"]
    assert updated_task["priority"] == update_data["priority"]
    assert updated_task["status"] == update_data["status"]
    assert updated_task["due_date"] == update_data["due_date"]

def test_update_nonexistent_task(client, sample_task_data):
    """Test updating a task that doesn't exist"""
    nonexistent_id = uuid4()
    update_data = {
        "title": "Updated Task"
    }
    response = client.put(f"/tasks/{nonexistent_id}", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_update_task_partial(client, sample_task_data):
    """Test updating only some fields of a task"""
    # Create a task
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    task_id = create_response.json()["task_id"]
    
    # Update only the title
    update_data = {
        "title": "Updated Task"
    }
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    
    # Verify only the title was updated
    updated_task = response.json()
    assert updated_task["title"] == update_data["title"]
    assert updated_task["description"] == sample_task_data["description"]  # Unchanged
    assert updated_task["priority"] == sample_task_data["priority"]  # Unchanged
    assert updated_task["status"] == sample_task_data["status"]  # Unchanged
    assert updated_task["due_date"] == sample_task_data["due_date"]  # Unchanged

def test_update_task_invalid_data(client, sample_task_data):
    """Test updating a task with invalid data"""
    # Create a task
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    task_id = create_response.json()["task_id"]
    
    # Update with invalid data
    update_data = {
        "title": "",  # Empty title
        "priority": 4  # Invalid priority
    }
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 422  # Validation error

def test_update_task_invalid_id_format(client, sample_task_data):
    """Test updating a task with an invalid ID format"""
    update_data = {
        "title": "Updated Task"
    }
    response = client.put("/tasks/invalid-id", json=update_data)
    assert response.status_code == 422  # Validation error

# Tests for DELETE /tasks/{task_id}
def test_delete_task(client, sample_task_data):
    """Test deleting a task"""
    # Create a task
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    task_id = create_response.json()["task_id"]
    
    # Delete the task
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Task deleted"
    
    # Verify the task is deleted
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_task(client):
    """Test deleting a task that doesn't exist"""
    nonexistent_id = uuid4()
    response = client.delete(f"/tasks/{nonexistent_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_delete_task_invalid_id_format(client):
    """Test deleting a task with an invalid ID format"""
    response = client.delete("/tasks/invalid-id")
    assert response.status_code == 422  # Validation error

# Tests for PATCH /tasks/{task_id}/status
def test_update_task_status(client, sample_task_data):
    """Test updating a task's status"""
    # Create a task with PENDING status (default)
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    task_id = create_response.json()["task_id"]
    
    # Update the status to COMPLETED
    response = client.patch(f"/tasks/{task_id}/status?status=1")  # 1 is COMPLETED
    assert response.status_code == 200
    
    # Verify the status update
    updated_task = response.json()
    assert updated_task["status"] == StatusOfTask.COMPLETED
    
    # Update the status back to PENDING
    response = client.patch(f"/tasks/{task_id}/status?status=0")  # 0 is PENDING
    assert response.status_code == 200
    
    # Verify the status update
    updated_task = response.json()
    assert updated_task["status"] == StatusOfTask.PENDING

def test_update_task_status_nonexistent_task(client):
    """Test updating the status of a task that doesn't exist"""
    nonexistent_id = uuid4()
    response = client.patch(f"/tasks/{nonexistent_id}/status?status=1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_update_task_status_invalid_status(client, sample_task_data):
    """Test updating a task's status with an invalid status"""
    # Create a task
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    task_id = create_response.json()["task_id"]
    
    # Update with invalid status
    response = client.patch(f"/tasks/{task_id}/status?status=2")  # Invalid status
    assert response.status_code == 422  # Validation error

def test_update_task_status_invalid_id_format(client, sample_task_data):
    """Test updating a task's status with an invalid ID format"""
    response = client.patch("/tasks/invalid-id/status?status=1")
    assert response.status_code == 422  # Validation error
