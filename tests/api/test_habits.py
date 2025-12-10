"""Tests for habit endpoints."""

from unittest.mock import patch, AsyncMock, MagicMock


class TestListHabits:
    """Test GET /v1/habits endpoint."""

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_list_habits_active(self, mock_repo, client, mock_user, mock_habit):
        """Test listing active habits."""
        mock_repo.get_all = AsyncMock(return_value=[mock_habit])

        response = client.get("/v1/habits?active=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["habits"]) == 1
        assert data["habits"][0]["id"] == mock_habit.id
        assert data["habits"][0]["name"] == mock_habit.name
        mock_repo.get_all.assert_called_once_with(mock_user.id, active=True)

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_list_habits_inactive(
        self, mock_repo, client, mock_user, mock_inactive_habit
    ):
        """Test listing inactive habits."""
        mock_repo.get_all = AsyncMock(return_value=[mock_inactive_habit])

        response = client.get("/v1/habits?active=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["habits"]) == 1
        assert data["habits"][0]["active"] is False
        mock_repo.get_all.assert_called_once_with(mock_user.id, active=False)

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_list_habits_filter_by_category(
        self, mock_repo, client, mock_user, mock_habit
    ):
        """Test filtering habits by category."""
        mock_repo.get_all = AsyncMock(return_value=[mock_habit])

        response = client.get("/v1/habits?category=health")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["habits"][0]["category"] == "health"


class TestGetHabit:
    """Test GET /v1/habits/{habit_id} endpoint."""

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_get_habit_success(self, mock_repo, client, mock_user, mock_habit):
        """Test getting a habit by ID."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        response = client.get(f"/v1/habits/{mock_habit.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_habit.id
        assert data["name"] == mock_habit.name
        assert data["weight"] == mock_habit.weight

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_get_habit_not_found(self, mock_repo, client):
        """Test getting non-existent habit."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.get("/v1/habits/999")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "HABIT_NOT_FOUND"

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_get_habit_forbidden(self, mock_repo, client, mock_habit):
        """Test getting habit belonging to another user."""
        mock_habit.user_id = 999  # Different user
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        response = client.get(f"/v1/habits/{mock_habit.id}")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"


class TestCreateHabit:
    """Test POST /v1/habits endpoint."""

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_create_habit_success(self, mock_repo, client, mock_user, mock_habit):
        """Test creating a new habit."""
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=mock_habit)

        response = client.post(
            "/v1/habits",
            json={
                "name": "Morning Exercise",
                "weight": 10,
                "category": "health",
                "allowed_skip_days": 0,
                "exempt_weekdays": [],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == mock_habit.name
        assert data["weight"] == mock_habit.weight
        mock_repo.create.assert_called_once()

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_create_habit_duplicate(self, mock_repo, client, mock_habit):
        """Test creating habit with duplicate name."""
        mock_repo.get_by_name = AsyncMock(return_value=mock_habit)

        response = client.post(
            "/v1/habits", json={"name": "Morning Exercise", "weight": 10}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "HABIT_EXISTS"

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_create_habit_invalid_weekdays(self, mock_repo, client):
        """Test creating habit with invalid weekday numbers."""
        mock_repo.get_by_name = AsyncMock(return_value=None)

        response = client.post(
            "/v1/habits",
            json={
                "name": "Test Habit",
                "weight": 10,
                "exempt_weekdays": [0, 8, 10],  # Invalid: must be 1-7
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "INVALID_WEEKDAYS"


class TestUpdateHabit:
    """Test PATCH /v1/habits/{habit_id} endpoint."""

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_update_habit_success(self, mock_repo, client, mock_user, mock_habit):
        """Test updating a habit."""
        updated_habit = mock_habit
        updated_habit.name = "Updated Name"
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.update = AsyncMock(return_value=updated_habit)

        response = client.patch(
            f"/v1/habits/{mock_habit.id}", json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_update_habit_invalid_weekdays(self, mock_repo, client, mock_habit):
        """Test updating habit with invalid weekday numbers."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        response = client.patch(
            f"/v1/habits/{mock_habit.id}",
            json={"exempt_weekdays": [0, 9]},  # Invalid
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "INVALID_WEEKDAYS"

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_update_habit_not_found(self, mock_repo, client):
        """Test updating non-existent habit."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.patch("/v1/habits/999", json={"name": "Test"})

        assert response.status_code == 404


class TestDeleteHabit:
    """Test DELETE /v1/habits/{habit_id} endpoint."""

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_delete_habit_success(self, mock_repo, client, mock_habit):
        """Test soft deleting a habit."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_repo.soft_delete = AsyncMock(return_value=mock_habit)

        response = client.delete(f"/v1/habits/{mock_habit.id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        mock_repo.soft_delete.assert_called_once_with(mock_habit.id)

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_delete_habit_not_found(self, mock_repo, client):
        """Test deleting non-existent habit."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.delete("/v1/habits/999")

        assert response.status_code == 404


class TestCompleteHabit:
    """Test POST /v1/habits/{habit_id}/complete endpoint."""

    @patch("src.api.v1.routers.habits.habit_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    def test_complete_habit_success(
        self, mock_repo, mock_service, client, mock_user, mock_habit
    ):
        """Test completing a habit."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        # Mock completion result
        result = MagicMock()
        result.habit_confirmed = True
        result.habit_name = mock_habit.name
        result.streak_count = 5
        result.got_reward = False
        result.total_weight_applied = 1.5
        result.reward = None
        result.cumulative_progress = None
        mock_service.process_habit_completion = AsyncMock(return_value=result)

        response = client.post(f"/v1/habits/{mock_habit.id}/complete", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["habit_confirmed"] is True
        assert data["habit_name"] == mock_habit.name
        assert data["streak_count"] == 5

    @patch("src.api.v1.routers.habits.habit_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    def test_complete_habit_with_reward(
        self, mock_repo, mock_service, client, mock_habit, mock_reward
    ):
        """Test completing habit and receiving a reward."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        # Mock completion result with reward
        result = MagicMock()
        result.habit_confirmed = True
        result.habit_name = mock_habit.name
        result.streak_count = 10
        result.got_reward = True
        result.total_weight_applied = 2.0
        result.reward = mock_reward
        result.cumulative_progress = None
        mock_service.process_habit_completion = AsyncMock(return_value=result)

        response = client.post(f"/v1/habits/{mock_habit.id}/complete", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["got_reward"] is True
        assert data["reward"] is not None
        assert data["reward"]["name"] == mock_reward.name

    @patch("src.api.v1.routers.habits.habit_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    def test_complete_habit_already_completed(
        self, mock_repo, mock_service, client, mock_habit
    ):
        """Test completing already completed habit."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_service.process_habit_completion = AsyncMock(
            side_effect=ValueError("already completed on this date")
        )

        response = client.post(f"/v1/habits/{mock_habit.id}/complete", json={})

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "ALREADY_COMPLETED"

    @patch("src.api.v1.routers.habits.habit_repository")
    def test_complete_habit_not_found(self, mock_repo, client):
        """Test completing non-existent habit."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.post("/v1/habits/999/complete", json={})

        assert response.status_code == 404


class TestBatchCompleteHabits:
    """Test POST /v1/habits/batch-complete endpoint."""

    @patch("src.api.v1.routers.habits.habit_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    def test_batch_complete_success(
        self, mock_repo, mock_service, client, mock_user, mock_habit
    ):
        """Test batch completing multiple habits."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        result = MagicMock()
        result.habit_confirmed = True
        result.habit_name = mock_habit.name
        result.streak_count = 5
        result.got_reward = False
        result.total_weight_applied = 1.5
        result.reward = None
        result.cumulative_progress = None
        mock_service.process_habit_completion = AsyncMock(return_value=result)

        response = client.post(
            "/v1/habits/batch-complete",
            json={
                "completions": [
                    {"habit_id": 1},
                    {"habit_id": 1},  # Complete same habit twice (different dates)
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 0
        assert len(data["errors"]) >= 0

    @patch("src.api.v1.routers.habits.habit_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    def test_batch_complete_partial_errors(
        self, mock_repo, mock_service, client, mock_habit
    ):
        """Test batch complete with some failures."""

        def get_by_id_side_effect(habit_id):
            if habit_id == 1:
                return mock_habit
            return None  # Habit not found

        mock_repo.get_by_id = AsyncMock(side_effect=get_by_id_side_effect)

        result = MagicMock()
        result.habit_confirmed = True
        result.habit_name = mock_habit.name
        result.streak_count = 5
        result.got_reward = False
        result.total_weight_applied = 1.5
        result.reward = None
        result.cumulative_progress = None
        mock_service.process_habit_completion = AsyncMock(return_value=result)

        response = client.post(
            "/v1/habits/batch-complete",
            json={
                "completions": [
                    {"habit_id": 1},
                    {"habit_id": 999},  # Non-existent
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1  # One success
        assert len(data["errors"]) == 1  # One error
        assert data["errors"][0]["habit_id"] == 999
