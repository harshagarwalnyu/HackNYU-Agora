from app.graph.builder import routing_decision
from app.graph.state import RoutingDecision, create_initial_state

def test_routing_decision_quiz():
    """Test that routing_decision returns 'quiz' when routing is QUIZ_ME."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    state["routing"] = RoutingDecision.QUIZ_ME

    assert routing_decision(state) == "quiz"

def test_routing_decision_socrates_new_question():
    """Test that routing_decision returns 'socrates' when routing is NEW_QUESTION."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    state["routing"] = RoutingDecision.NEW_QUESTION

    assert routing_decision(state) == "socrates"

def test_routing_decision_socrates_answer_to_my_question():
    """Test that routing_decision returns 'socrates' when routing is ANSWER_TO_MY_QUESTION."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    state["routing"] = RoutingDecision.ANSWER_TO_MY_QUESTION

    assert routing_decision(state) == "socrates"

def test_routing_decision_socrates_frustrated_interruption():
    """Test that routing_decision returns 'socrates' when routing is FRUSTRATED_INTERRUPTION."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    state["routing"] = RoutingDecision.FRUSTRATED_INTERRUPTION

    assert routing_decision(state) == "socrates"

def test_routing_decision_socrates_request_for_visual():
    """Test that routing_decision returns 'socrates' when routing is REQUEST_FOR_VISUAL."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    state["routing"] = RoutingDecision.REQUEST_FOR_VISUAL

    assert routing_decision(state) == "socrates"

def test_routing_decision_none():
    """Test that routing_decision returns 'socrates' when routing is None."""
    state = create_initial_state(user_id="test_user", session_id="test_session")
    state["routing"] = None

    assert routing_decision(state) == "socrates"
