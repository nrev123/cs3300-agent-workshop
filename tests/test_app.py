import pytest

from app import app, tasks


@pytest.fixture
def client():
    """Create a Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset the in-memory task list before each test."""
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Project-1 Report"},
        {"id": 2, "title": "Project-2 MMFs"}
    ])


def test_index(client):
    """Render the task tracker page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Task Tracker" in response.data


def test_get_tasks(client):
    """Return all tasks with a default priority."""
    response = client.get('/api/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert all(task['priority'] == 'Medium' for task in data)


def test_get_tasks_preserves_existing_priority(client):
    """Preserve the priority stored on an existing task."""
    tasks[0]['priority'] = 'High'

    response = client.get('/api/tasks')

    assert response.status_code == 200
    data = response.get_json()
    assert data[0]['priority'] == 'High'
    assert data[1]['priority'] == 'Medium'


@pytest.mark.parametrize('priority', ['Low', 'Medium', 'High'])
def test_add_task_with_priority(client, priority):
    """Create a task with each supported priority."""
    response = client.post(
        '/api/tasks',
        json={"title": "Prioritized task", "priority": priority}
    )

    assert response.status_code == 201
    assert response.get_json()['priority'] == priority

    tasks_response = client.get('/api/tasks')
    created_task = tasks_response.get_json()[-1]
    assert created_task['priority'] == priority


def test_add_task_defaults_to_medium_priority(client):
    """Default a task priority to Medium when it is omitted."""
    response = client.post('/api/tasks', json={"title": "Default task"})

    assert response.status_code == 201
    assert response.get_json()['priority'] == 'Medium'


def test_add_task_defaults_to_medium_for_empty_priority(client):
    """Default a task priority to Medium when it is empty."""
    response = client.post(
        '/api/tasks',
        json={"title": "Empty priority task", "priority": ""}
    )

    assert response.status_code == 201
    assert response.get_json()['priority'] == 'Medium'


def test_add_task_rejects_invalid_priority(client):
    """Reject priorities outside the supported set."""
    response = client.post(
        '/api/tasks',
        json={"title": "Invalid task", "priority": "Urgent"}
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'Invalid priority'
    assert len(client.get('/api/tasks').get_json()) == 2


def test_add_task_rejects_unhashable_priority(client):
    """Reject malformed unhashable priority values with a client error."""
    response = client.post(
        '/api/tasks',
        json={"title": "Malformed task", "priority": []}
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'Invalid priority'
    assert len(client.get('/api/tasks').get_json()) == 2


def test_add_task_missing_title(client):
    """Reject task creation when the title is missing."""
    response = client.post('/api/tasks', json={"wrong_key": "value"})
    assert response.status_code == 400
    assert "error" in response.get_json()

    response = client.post('/api/tasks', json={})
    assert response.status_code == 400


def test_delete_task(client):
    """Delete an existing task."""
    response = client.delete('/api/tasks/1')
    assert response.status_code == 200
    get_response = client.get('/api/tasks')
    data = get_response.get_json()
    assert len(data) == 1
    assert data[0]['id'] == 2
