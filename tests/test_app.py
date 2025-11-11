"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy(),
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state
    for name in list(activities.keys()):
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRoot:
    """Test the root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test the GET /activities endpoint"""
    
    def test_get_activities_returns_dict(self, client, reset_activities):
        """Test that /activities returns a dictionary of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify it's a dict
        assert isinstance(data, dict)
        
        # Verify expected activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        
    def test_get_activities_has_required_fields(self, client, reset_activities):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_get_activities_participants_are_strings(self, client, reset_activities):
        """Test that participant emails are strings"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_data in data.values():
            for participant in activity_data["participants"]:
                assert isinstance(participant, str)


class TestSignup:
    """Test the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_student(self, client, reset_activities):
        """Test signing up a new student for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=alice@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "alice@mergington.edu" in data["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant to the list"""
        email = "bob@mergington.edu"
        initial_count = len(activities["Chess Club"]["participants"])
        
        response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 200
        assert len(activities["Chess Club"]["participants"]) == initial_count + 1
        assert email in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_student_fails(self, client, reset_activities):
        """Test that a student can't sign up twice for the same activity"""
        email = "michael@mergington.edu"  # Already signed up for Chess Club
        
        response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity_fails(self, client, reset_activities):
        """Test that signing up for a non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple activities"""
        email = "charlie@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            f"/activities/Programming Class/signup?email={email}"
        )
        assert response2.status_code == 200
        
        # Verify both signups worked
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestUnregister:
    """Test the POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        email = "michael@mergington.edu"  # Already signed up for Chess Club
        
        response = client.post(
            f"/activities/Chess Club/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert email not in activities["Chess Club"]["participants"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "daniel@mergington.edu"  # Already signed up for Chess Club
        initial_count = len(activities["Chess Club"]["participants"])
        
        response = client.post(
            f"/activities/Chess Club/unregister?email={email}"
        )
        assert response.status_code == 200
        assert len(activities["Chess Club"]["participants"]) == initial_count - 1
    
    def test_unregister_nonexistent_participant_fails(self, client, reset_activities):
        """Test that unregistering a non-participant fails"""
        email = "nothere@mergington.edu"
        
        response = client.post(
            f"/activities/Chess Club/unregister?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity_fails(self, client, reset_activities):
        """Test that unregistering from a non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_after_unregister(self, client, reset_activities):
        """Test that a student can re-sign up after unregistering"""
        email = "michael@mergington.edu"
        
        # Unregister
        response1 = client.post(
            f"/activities/Chess Club/unregister?email={email}"
        )
        assert response1.status_code == 200
        assert email not in activities["Chess Club"]["participants"]
        
        # Re-register
        response2 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response2.status_code == 200
        assert email in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for complex workflows"""
    
    def test_full_signup_workflow(self, client, reset_activities):
        """Test a complete signup workflow"""
        # Get initial activities
        response1 = client.get("/activities")
        initial_activities = response1.json()
        chess_initial_count = len(initial_activities["Chess Club"]["participants"])
        
        # Sign up a new student
        email = "diana@mergington.edu"
        response2 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response2.status_code == 200
        
        # Verify the signup in the data
        response3 = client.get("/activities")
        updated_activities = response3.json()
        assert len(updated_activities["Chess Club"]["participants"]) == chess_initial_count + 1
        assert email in updated_activities["Chess Club"]["participants"]
    
    def test_concurrent_activity_operations(self, client, reset_activities):
        """Test multiple operations on different activities"""
        email1 = "eve@mergington.edu"
        email2 = "frank@mergington.edu"
        
        # Sign up to different activities
        response1 = client.post(
            f"/activities/Chess Club/signup?email={email1}"
        )
        response2 = client.post(
            f"/activities/Programming Class/signup?email={email2}"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both are in their respective activities
        response3 = client.get("/activities")
        activities_data = response3.json()
        assert email1 in activities_data["Chess Club"]["participants"]
        assert email2 in activities_data["Programming Class"]["participants"]
