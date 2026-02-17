import time
from app.graph.state import add_message, create_initial_state

def test_add_message():
    """Test that add_message correctly adds a message to the state."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    initial_message_count = len(state["messages"])

    role = "student"
    content = "Hello, tutor!"

    # We can't easily mock time.time() inside the function without more complex patching,
    # but we can check if the timestamp is reasonable.
    before = time.time()
    updated_state = add_message(state, role, content)
    after = time.time()

    assert len(updated_state["messages"]) == initial_message_count + 1
    new_message = updated_state["messages"][-1]

    assert new_message["role"] == role
    assert new_message["content"] == content
    assert before <= new_message["timestamp"] <= after

def test_add_message_tutor():
    """Test adding a tutor message."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    role = "tutor"
    content = "Hello, student!"

    updated_state = add_message(state, role, content)

    new_message = updated_state["messages"][-1]
    assert new_message["role"] == role
    assert new_message["content"] == content
