import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from api.app import app, tasks_db

@pytest.fixture(scope="function")
def client():
    # Clear the database before each test
    tasks_db.clear()
    with TestClient(app) as c:
        yield c

@pytest.fixture
def sample_task_data():
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": 2,  # MEDIUM
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }

@pytest.fixture
def sample_task_update_data():
    return {
        "title": "Updated Test Task",
        "description": "This is an updated test task",
        "priority": 3,  # HIGH
        "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
        "status": 1  # COMPLETED
    }

# POST /tasks - Create a new task
def test_create_task(client, sample_task_data):
    # Test successful creation
    response = client.post("/tasks", json=sample_task_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_task_data["title"]
    assert data["description"] == sample_task_data["description"]
    assert data["priority"] == sample_task_data["priority"]
    assert data["status"] == 0  # Default status is PENDING
    assert "task_id" in data
    assert data["due_date"] == sample_task_data["due_date"]

def test_create_task_missing_required_fields(client):
    # Test missing required fields
    incomplete_data = {
        "title": "Test Task"
    }
    response = client.post("/tasks", json=incomplete_data)
    assert response.status_code == 422

def test_create_task_invalid_title(client):
    # Test invalid title (too short)
    invalid_data = {
        "title": "",  # Empty title
        "priority": 2,
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=invalid_data)
    assert response.status_code == 422

def test_create_task_invalid_priority(client):
    # Test invalid priority
    invalid_data = {
        "title": "Test Task",
        "priority": 4,  # Invalid priority
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=invalid_data)
    assert response.status_code == 422

def test_create_task_past_due_date(client):
    # Test past due date
    invalid_data = {
        "title": "Test Task",
        "priority": 2,
        "due_date": (datetime.now() - timedelta(days=1)).isoformat()
    }
    response = client.post("/tasks", json=invalid_data)
    assert response.status_code == 422

# GET /tasks - List tasks with optional filtering
def test_list_tasks(client, sample_task_data):
    # Create a task first
    client.post("/tasks", json=sample_task_data)
    
    # Test listing all tasks
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == sample_task_data["title"]

def test_list_tasks_with_status_filter(client, sample_task_data):
    # Create multiple tasks with different statuses
    client.post("/tasks", json={**sample_task_data, "status": 0})  # PENDING
    client.post("/tasks", json={**sample_task_data, "status": 1})  # COMPLETED
    
    # Test filtering by status
    response = client.get("/tasks?status=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == 0  # PENDING

def test_list_tasks_with_priority_filter(client, sample_task_data):
    # Create multiple tasks with different priorities
    client.post("/tasks", json={**sample_task_data, "priority": 1})  # LOW
    client.post("/tasks", json={**sample_task_data, "priority": 2})  # MEDIUM
    
    # Test filtering by priority
    response = client.get("/tasks?priority=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["priority"] == 1  # LOW

def test_list_tasks_with_both_filters(client, sample_task_data):
    # Create multiple tasks with different statuses and priorities
    client.post("/tasks", json={**sample_task_data, "status": 0, "priority": 1})  # PENDING, LOW
    client.post("/tasks", json={**sample_task_data, "status": 1, "priority": 2})  # COMPLETED, MEDIUM
    client.post("/tasks", json={**sample_task_data, "status": 0, "priority": 2})  # PENDING, MEDIUM
    
    # Test filtering by both status and priority
    response = client.get("/tasks?status=0&priority=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == 0  # PENDING
    assert data[0]["priority"] == 2  # MEDIUM

def test_list_tasks_empty_database(client):
    # Test listing tasks when database is empty
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

# GET /tasks/{task_id} - Get a specific task
def test_get_task(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test getting the task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_task_data["title"]
    assert data["task_id"] == task_id

def test_get_nonexistent_task(client):
    # Test getting a non-existent task
    nonexistent_id = uuid4()
    response = client.get(f"/tasks/{nonexistent_id}")
    assert response.status_code == 404

def test_get_task_invalid_uuid(client):
    # Test getting a task with invalid UUID
    response = client.get("/tasks/invalid-uuid")
    assert response.status_code == 422

# PUT /tasks/{task_id} - Update a task
def test_update_task(client, sample_task_data, sample_task_update_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test updating the task
    response = client.put(f"/tasks/{task_id}", json=sample_task_update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_task_update_data["title"]
    assert data["description"] == sample_task_update_data["description"]
    assert data["priority"] == sample_task_update_data["priority"]
    assert data["status"] == sample_task_update_data["status"]
    assert data["due_date"] == sample_task_update_data["due_date"]

def test_update_nonexistent_task(client, sample_task_update_data):
    # Test updating a non-existent task
    nonexistent_id = uuid4()
    response = client.put(f"/tasks/{nonexistent_id}", json=sample_task_update_data)
    assert response.status_code == 404

def test_update_task_partial(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test updating only some fields
    partial_update = {
        "title": "Partially Updated Task",
        "status": 1  # COMPLETED
    }
    response = client.put(f"/tasks/{task_id}", json=partial_update)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == partial_update["title"]
    assert data["status"] == partial_update["status"]
    # Other fields should remain unchanged
    assert data["description"] == sample_task_data["description"]
    assert data["priority"] == sample_task_data["priority"]
    assert data["due_date"] == sample_task_data["due_date"]

def test_update_task_invalid_uuid(client, sample_task_update_data):
    # Test updating a task with invalid UUID
    response = client.put("/tasks/invalid-uuid", json=sample_task_update_data)
    assert response.status_code == 422

def test_update_task_invalid_data(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test updating with invalid data
    invalid_update = {
        "title": "",  # Empty title is invalid
        "priority": 2,
        "due_date": (datetime.now() + timedelta(days=1)).isoformat()
    }
    response = client.put(f"/tasks/{task_id}", json=invalid_update)
    assert response.status_code == 422

# DELETE /tasks/{task_id} - Delete a task
def test_delete_task(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test deleting the task
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json() == {"detail": "Task deleted"}
    
    # Verify the task is actually deleted
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_task(client):
    # Test deleting a non-existent task
    nonexistent_id = uuid4()
    response = client.delete(f"/tasks/{nonexistent_id}")
    assert response.status_code == 404

def test_delete_task_invalid_uuid(client):
    # Test deleting a task with invalid UUID
    response = client.delete("/tasks/invalid-uuid")
    assert response.status_code == 422

# PATCH /tasks/{task_id}/status - Update task status
def test_update_status(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test updating the status to COMPLETED
    response = client.patch(f"/tasks/{task_id}/status?status=1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == 1  # COMPLETED
    
    # Test updating the status back to PENDING
    response = client.patch(f"/tasks/{task_id}/status?status=0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == 0  # PENDING

def test_update_status_nonexistent_task(client):
    # Test updating status of a non-existent task
    nonexistent_id = uuid4()
    response = client.patch(f"/tasks/{nonexistent_id}/status?status=1")
    assert response.status_code == 404

def test_update_status_invalid_uuid(client):
    # Test updating status with invalid UUID
    response = client.patch("/tasks/invalid-uuid/status?status=1")
    assert response.status_code == 422

def test_update_status_invalid_status(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test updating with invalid status
    response = client.patch(f"/tasks/{task_id}/status?status=2")  # Invalid status
    assert response.status_code == 422

def test_update_status_missing_status_param(client, sample_task_data):
    # Create a task first
    create_response = client.post("/tasks", json=sample_task_data)
    task_id = create_response.json()["task_id"]
    
    # Test updating without status parameter
    response = client.patch(f"/tasks/{task_id}/status")
    assert response.status_code == 422

# Performance and Edge Cases
def test_create_many_tasks_performance(client, sample_task_data):
    # Test creating many tasks to check performance
    num_tasks = 100
    for i in range(num_tasks):
        task_data = {
            **sample_task_data,
            "title": f"Task {i}",
            "description": f"Description for task {i}"
        }
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 200
    
    # Verify all tasks were created
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == num_tasks

def test_list_tasks_with_filters_performance(client, sample_task_data):
    # Create many tasks with different statuses and priorities
    num_tasks = 100
    for i in range(num_tasks):
        status = i % 2  # Alternate between PENDING and COMPLETED
        priority = (i % 3) + 1  # Cycle through LOW, MEDIUM, HIGH
        task_data = {
            **sample_task_data,
            "title": f"Task {i}",
            "description": f"Description for task {i}",
            "status": status,
            "priority": priority
        }
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 200
    
    # Test filtering performance
    response = client.get("/tasks?status=0&priority=2")
    assert response.status_code == 200
    data = response.json()
    # Should have approximately 33 tasks (100/3) with priority 2
    assert len(data) == 34  # 34 because 100/3 = 33.33, rounded up

def test_long_description(client, sample_task_data):
    # Test with a very long description (at the limit)
    long_description = "a" * 500  # Max length is 500
    task_data = {
        **sample_task_data,
        "description": long_description
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == long_description

def test_long_description_exceeds_limit(client, sample_task_data):
    # Test with a description that exceeds the limit
    long_description = "a" * 501  # Exceeds max length of 500
    task_data = {
        **sample_task_data,
        "description": long_description
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_long_title(client, sample_task_data):
    # Test with a very long title (at the limit)
    long_title = "a" * 100  # Max length is 100
    task_data = {
        **sample_task_data,
        "title": long_title
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == long_title

def test_long_title_exceeds_limit(client, sample_task_data):
    # Test with a title that exceeds the limit
    long_title = "a" * 101  # Exceeds max length of 100
    task_data = {
        **sample_task_data,
        "title": long_title
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_empty_title(client, sample_task_data):
    # Test with an empty title
    task_data = {
        **sample_task_data,
        "title": ""
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_whitespace_title(client, sample_task_data):
    # Test with a title that only contains whitespace
    task_data = {
        **sample_task_data,
        "title": "   "
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_due_date_far_future(client, sample_task_data):
    # Test with a due date far in the future
    far_future_date = (datetime.now() + timedelta(days=365*10)).isoformat()  # 10 years from now
    task_data = {
        **sample_task_data,
        "due_date": far_future_date
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 200
    data = response.json()
    assert data["due_date"] == far_future_date

def test_due_date_just_now(client, sample_task_data):
    # Test with a due date that's just now (should be valid as it's not in the past)
    just_now = datetime.now().isoformat()
    task_data = {
        **sample_task_data,
        "due_date": just_now
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 200
    data = response.json()
    assert data["due_date"] == just_now
