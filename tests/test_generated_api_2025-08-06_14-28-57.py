import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient

# Import the app from the correct location
from api.app import app, tasks_db, TaskPriority, StatusOfTask

# Clear the database before each test
@pytest.fixture(autouse=True)
def clear_database():
    tasks_db.clear()
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_task_data():
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }

# Test for POST /tasks
def test_create_task(client, sample_task_data):
    response = client.post("/tasks", json=sample_task_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_task_data["title"]
    assert data["description"] == sample_task_data["description"]
    assert data["priority"] == sample_task_data["priority"]
    assert "task_id" in data
    assert data["status"] == StatusOfTask.PENDING  # Default status

def test_create_task_missing_required_field(client):
    invalid_data = {
        "description": "This is a test task",
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=invalid_data)
    assert response.status_code == 422

def test_create_task_invalid_priority(client):
    invalid_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": 5,  # Invalid priority
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=invalid_data)
    assert response.status_code == 422

def test_create_task_past_due_date(client):
    invalid_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() - timedelta(days=1)).isoformat()  # Past date
    }
    response = client.post("/tasks", json=invalid_data)
    assert response.status_code == 422

# Test for GET /tasks
def test_list_tasks_empty(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []

def test_list_tasks_with_data(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    assert create_response.status_code == 200
    
    # List tasks
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == sample_task_data["title"]

def test_list_tasks_filter_by_status(client, sample_task_data):
    # Create multiple tasks with different statuses
    client.post("/tasks", json={**sample_task_data, "status": StatusOfTask.PENDING})
    client.post("/tasks", json={**sample_task_data, "status": StatusOfTask.COMPLETED})
    
    # Filter by PENDING status
    response = client.get("/tasks?status=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == StatusOfTask.PENDING
    
    # Filter by COMPLETED status
    response = client.get("/tasks?status=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == StatusOfTask.COMPLETED

def test_list_tasks_filter_by_priority(client, sample_task_data):
    # Create multiple tasks with different priorities
    client.post("/tasks", json={**sample_task_data, "priority": TaskPriority.LOW})
    client.post("/tasks", json={**sample_task_data, "priority": TaskPriority.HIGH})
    
    # Filter by LOW priority
    response = client.get("/tasks?priority=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["priority"] == TaskPriority.LOW
    
    # Filter by HIGH priority
    response = client.get("/tasks?priority=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["priority"] == TaskPriority.HIGH

def test_list_tasks_filter_by_status_and_priority(client, sample_task_data):
    # Create multiple tasks with different combinations
    client.post("/tasks", json={**sample_task_data, "status": StatusOfTask.PENDING, "priority": TaskPriority.LOW})
    client.post("/tasks", json={**sample_task_data, "status": StatusOfTask.COMPLETED, "priority": TaskPriority.HIGH})
    client.post("/tasks", json={**sample_task_data, "status": StatusOfTask.PENDING, "priority": TaskPriority.HIGH})
    
    # Filter by PENDING status and HIGH priority
    response = client.get("/tasks?status=0&priority=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == StatusOfTask.PENDING
    assert data[0]["priority"] == TaskPriority.HIGH

# Test for GET /tasks/{task_id}
def test_get_task(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Get the task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == str(task_id)
    assert data["title"] == sample_task_data["title"]

def test_get_nonexistent_task(client):
    task_id = uuid4()
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

# Test for PUT /tasks/{task_id}
def test_update_task(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update the task
    update_data = {
        "title": "Updated Task",
        "description": "Updated description",
        "priority": TaskPriority.MEDIUM,
        "due_date": (datetime.now() + timedelta(days=2)).isoformat()
    }
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]
    assert data["priority"] == update_data["priority"]

def test_update_partial_task(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update only the title
    update_data = {"title": "Updated Task"}
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    # Other fields should remain unchanged
    assert data["description"] == sample_task_data["description"]
    assert data["priority"] == sample_task_data["priority"]

def test_update_nonexistent_task(client, sample_task_data):
    task_id = uuid4()
    update_data = {"title": "Updated Task"}
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_update_task_invalid_data(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update with invalid data
    update_data = {
        "title": "",  # Empty title
        "priority": TaskPriority.HIGH
    }
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 422

# Test for DELETE /tasks/{task_id}
def test_delete_task(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Delete the task
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Task deleted"
    
    # Verify task is deleted
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_task(client):
    task_id = uuid4()
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

# Test for PATCH /tasks/{task_id}/status
def test_update_status(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update status to COMPLETED
    response = client.patch(f"/tasks/{task_id}/status?status=1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == StatusOfTask.COMPLETED
    
    # Update status back to PENDING
    response = client.patch(f"/tasks/{task_id}/status?status=0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == StatusOfTask.PENDING

def test_update_status_nonexistent_task(client):
    task_id = uuid4()
    response = client.patch(f"/tasks/{task_id}/status?status=1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_update_status_invalid_value(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update with invalid status value
    response = client.patch(f"/tasks/{task_id}/status?status=2")
    assert response.status_code == 422

# Performance tests
def test_create_task_performance(client, sample_task_data):
    # Create 100 tasks and measure time
    import time
    start_time = time.time()
    
    for _ in range(100):
        response = client.post("/tasks", json=sample_task_data)
        assert response.status_code == 200
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Should complete in under 5 seconds
    assert elapsed_time < 5

def test_list_tasks_performance(client, sample_task_data):
    # Create 100 tasks
    for _ in range(100):
        client.post("/tasks", json=sample_task_data)
    
    # List all tasks and measure time
    import time
    start_time = time.time()
    
    response = client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 100
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Should complete in under 1 second
    assert elapsed_time < 1

def test_list_tasks_filter_performance(client, sample_task_data):
    # Create 100 tasks with alternating statuses
    for i in range(100):
        status = StatusOfTask.PENDING if i % 2 == 0 else StatusOfTask.COMPLETED
        client.post("/tasks", json={**sample_task_data, "status": status})
    
    # Filter tasks and measure time
    import time
    start_time = time.time()
    
    response = client.get("/tasks?status=0")
    assert response.status_code == 200
    assert len(response.json()) == 50  # Half should be PENDING
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Should complete in under 1 second
    assert elapsed_time < 1

# Edge cases
def test_create_task_max_length_fields(client):
    # Test with maximum allowed lengths
    max_length_data = {
        "title": "a" * 100,  # Max length for title
        "description": "a" * 500,  # Max length for description
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=max_length_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == max_length_data["title"]
    assert data["description"] == max_length_data["description"]

def test_create_task_min_length_title(client):
    # Test with minimum allowed title length
    min_length_data = {
        "title": "a",  # Min length for title
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=min_length_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == min_length_data["title"]

def test_create_task_empty_description(client):
    # Test with empty description (should be allowed as it's optional)
    empty_desc_data = {
        "title": "Test Task",
        "description": "",  # Empty description
        "priority": TaskPriority.HIGH,
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=empty_desc_data)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == empty_desc_data["description"]

def test_update_task_empty_description(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update with empty description
    update_data = {"description": ""}
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == ""

def test_update_task_min_length_title(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update with minimum title length
    update_data = {"title": "a"}  # Min length for title
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]

def test_update_task_max_length_fields(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Update with maximum allowed lengths
    update_data = {
        "title": "a" * 100,  # Max length for title
        "description": "a" * 500  # Max length for description
    }
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]
