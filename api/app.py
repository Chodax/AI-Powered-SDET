from datetime import datetime
from enum import IntEnum
from typing import Optional, List
from uuid import uuid4, UUID

from anyio.abc import TaskStatus
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, validator, FutureDatetime


app = FastAPI()

tasks_db = {}


class TaskPriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class StatusOfTask(IntEnum):
    PENDING = 0
    COMPLETED = 1


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description='Title of the task')
    description: Optional[str] = Field(None, max_length=500, description='Description of the task')
    priority: TaskPriority = Field(..., description='Priority of the task')
    status: StatusOfTask = Field(StatusOfTask.PENDING, description='Status of the task')
    due_date: FutureDatetime = Field(..., description='Due date of the task')


class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    task_id: UUID = Field(..., description='Unique identifier of the task')

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100, description='Title of the task')
    description: Optional[str] = Field(None, max_length=500, description='Description of the task')
    priority: Optional[TaskPriority] = Field(None, description='Priority of the task')
    status: Optional[StatusOfTask] = Field(None, description='Status of the task')
    due_date: Optional[FutureDatetime] = Field(None, description='Due date of the task')


@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate):
    task_id = uuid4()
    # Mozda treba if za description ili model_dump
    new_task = Task(task_id=task_id,
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    due_date=task.due_date,
                    status=task.status)
    tasks_db[task_id] = new_task
    return new_task


@app.get("/tasks", response_model=List[Task])
def list_tasks(
    status: Optional[StatusOfTask] = Query(None),
    priority: Optional[TaskPriority] = Query(None)
):
    results = list(tasks_db.values())
    if status is not None:
        results = [t for t in results if t.status == status]
    if priority is not None:
        results = [t for t in results if t.priority == priority]
    return results


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: UUID):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: UUID, updated_task: TaskUpdate):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail='Task not found')

    task = tasks_db[task_id]
    update_data = updated_task.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: UUID):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    del tasks_db[task_id]
    return {"detail": "Task deleted"}

@app.patch("/tasks/{task_id}/status", response_model=Task)
def update_status(task_id: UUID, status: StatusOfTask):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = status
    return task
