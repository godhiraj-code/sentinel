import pytest
from sentinel.core.goal_parser import RegexGoalParser, GoalStep, TargetSpec

def test_parse_single_click():
    parser = RegexGoalParser()
    goal = "Click the Login button"
    parsed = parser.parse(goal)
    
    assert len(parsed.steps) == 1
    assert parsed.steps[0].action == "click"
    assert parsed.steps[0].target.text == "Login button"

def test_parse_multi_step_then():
    parser = RegexGoalParser()
    goal = "Login then verify 'Welcome' appears"
    parsed = parser.parse(goal)
    
    assert len(parsed.steps) == 2
    assert parsed.steps[0].action == "click"
    assert "login" in parsed.steps[0].target.text.lower()
    assert parsed.steps[1].action == "verify"
    assert parsed.steps[1].value == "Welcome"

def test_parse_multi_step_and_then():
    parser = RegexGoalParser()
    goal = "Type 'admin' in user field and then click Submit"
    parsed = parser.parse(goal)
    
    assert len(parsed.steps) == 2
    assert parsed.steps[0].action == "type"
    assert parsed.steps[0].value == "admin"
    assert "user" in parsed.steps[0].target.text.lower()
    assert parsed.steps[1].action == "click"
    assert parsed.steps[1].target.text == "Submit"

def test_parse_attributes():
    parser = RegexGoalParser()
    goal = "Click button with class btn-primary"
    parsed = parser.parse(goal)
    
    assert len(parsed.steps) == 1
    assert parsed.steps[0].action == "click"
    assert parsed.steps[0].target.css_class == "btn-primary"

def test_parse_complex_attributes():
    parser = RegexGoalParser()
    goal = "Type 'test' in input with id user-input and class dark-mode"
    parsed = parser.parse(goal)
    
    assert len(parsed.steps) == 1
    assert parsed.steps[0].action == "type"
    assert parsed.steps[0].value == "test"
    assert parsed.steps[0].target.id == "user-input"
    assert parsed.steps[0].target.css_class == "dark-mode"

def test_parse_navigate():
    parser = RegexGoalParser()
    goal = "Open https://google.com"
    parsed = parser.parse(goal)
    
    assert len(parsed.steps) == 1
    assert parsed.steps[0].action == "navigate"
    assert parsed.steps[0].value == "https://google.com"
