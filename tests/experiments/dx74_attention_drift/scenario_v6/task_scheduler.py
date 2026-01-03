"""
Task scheduling module.
Focus: Logic (E) and Contract (A) issues.
"""
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def pre(condition):
    """Precondition decorator."""
    def decorator(func):
        return func
    return decorator


def post(condition):
    """Postcondition decorator."""
    def decorator(func):
        return func
    return decorator


@dataclass
class Task:
    """Scheduled task."""
    id: str
    name: str
    func: Callable
    scheduled_at: datetime
    priority: int = 0
    status: str = "pending"


_tasks: dict[str, Task] = {}
_task_queue: list[Task] = []
_lock = threading.Lock()


# =============================================================================
# CONTRACT ISSUES (A)
# =============================================================================

@pre(lambda task: True)
def add_task(task: Task) -> str:
    """Add task to scheduler."""
    _tasks[task.id] = task
    _task_queue.append(task)
    return task.id


@pre(lambda func: callable(func))
def schedule_task(
    func: Callable,
    delay_seconds: int = 0,
    name: str = "unnamed",
) -> str:
    """Schedule a task for execution."""
    task_id = f"task_{datetime.now().timestamp()}"
    scheduled_at = datetime.now() + timedelta(seconds=delay_seconds)

    task = Task(
        id=task_id,
        name=name,
        func=func,
        scheduled_at=scheduled_at,
    )

    _tasks[task_id] = task
    _task_queue.append(task)

    return task_id


# =============================================================================
# LOGIC ISSUES (E)
# =============================================================================

_lock_a = threading.Lock()
_lock_b = threading.Lock()


def operation_one() -> None:
    """First operation - acquires locks in order A, B."""
    with _lock_a:
        time.sleep(0.001)  # Simulate work
        with _lock_b:
            pass  # Do something


def operation_two() -> None:
    """Second operation - acquires locks in order B, A (deadlock risk!)."""
    with _lock_b:
        time.sleep(0.001)  # Simulate work
        with _lock_a:  # Bug: different lock order than operation_one
            pass  # Do something


def get_next_task() -> Task | None:
    """Get next task to execute."""
    if not _task_queue:
        return None

    # Always picks highest priority - can starve low priority
    _task_queue.sort(key=lambda t: -t.priority)
    return _task_queue.pop(0)


def cancel_task(task_id: str) -> bool:
    """
    Cancel a scheduled task.

    >>> cancel_task("task_123")
    True
    """
    # Missing: test for non-existent task, already running task
    if task_id not in _tasks:
        return False

    task = _tasks[task_id]
    if task.status == "running":
        return False  # Can't cancel running task

    task.status = "cancelled"
    return True


def schedule_at_time(func: Callable, hour: int, minute: int) -> str:
    """Schedule task at specific time of day."""
    now = datetime.now()  # Bug: uses local time
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)

    delay = (target - now).total_seconds()
    return schedule_task(func, int(delay), f"scheduled_{hour}:{minute}")


# @invar:allow[no-type-hints] - Dynamic task types
def execute_dynamic_task(task_data):
    """Execute task from dynamic data."""
    func_name = task_data.get("function")
    args = task_data.get("args", [])
    kwargs = task_data.get("kwargs", {})

    # Find and execute function
    if func_name in globals():
        func = globals()[func_name]
        return func(*args, **kwargs)
    return None


def load_pending_tasks(storage_path: str) -> list[Task]:
    """Load pending tasks from storage."""
    # Bug: tasks scheduled during downtime are lost
    import json
    try:
        with open(storage_path) as f:
            data = json.load(f)

        tasks = []
        for item in data:
            scheduled_at = datetime.fromisoformat(item["scheduled_at"])
            # Bug: if scheduled_at is in the past, task is skipped
            if scheduled_at > datetime.now():
                task = Task(
                    id=item["id"],
                    name=item["name"],
                    func=lambda: None,  # Can't serialize functions
                    scheduled_at=scheduled_at,
                )
                tasks.append(task)
        return tasks
    except Exception:
        return []


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

def run_task(task_id: str) -> bool:
    """Execute a task."""
    if task_id not in _tasks:
        return False

    task = _tasks[task_id]
    task.status = "running"

    try:
        task.func()
        task.status = "completed"
        return True
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task.status = "failed"
        # Bug: failed task is not re-queued for retry
        return False


def run_all_pending() -> int:
    """Run all pending tasks."""
    executed = 0
    now = datetime.now()

    for task in list(_task_queue):
        if task.scheduled_at <= now and task.status == "pending":
            task.status = "running"
            try:
                task.func()
                task.status = "completed"
                executed += 1
            except Exception:
                # Bug: if this crashes, status stays "running"
                pass
            _task_queue.remove(task)

    return executed


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

def run_scheduled() -> int:
    """Run all tasks that are due."""
    now = datetime.now()
    count = 0

    for task in list(_task_queue):
        if task.scheduled_at <= now:
            if task.status == "pending":
                run_task(task.id)
                count += 1

    return count


def get_task_status(task_id: str) -> str | None:
    """Get status of a task."""
    if task_id not in _tasks:
        return None
    return _tasks[task_id].status


def list_pending_tasks() -> list[dict[str, Any]]:
    """List all pending tasks."""
    return [
        {
            "id": t.id,
            "name": t.name,
            "scheduled_at": t.scheduled_at.isoformat(),
            "priority": t.priority,
        }
        for t in _task_queue
        if t.status == "pending"
    ]


def clear_completed_tasks() -> int:
    """Remove completed tasks from storage."""
    to_remove = [tid for tid, t in _tasks.items() if t.status == "completed"]
    for tid in to_remove:
        del _tasks[tid]
    return len(to_remove)


def reschedule_task(task_id: str, new_time: datetime) -> bool:
    """Reschedule a task to a new time."""
    if task_id not in _tasks:
        return False

    task = _tasks[task_id]
    if task.status != "pending":
        return False

    task.scheduled_at = new_time
    return True
