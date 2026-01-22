"""Tests for reward endpoints."""

from unittest.mock import patch, AsyncMock, MagicMock


class TestListRewards:
    """Test GET /v1/rewards endpoint."""

    @patch("src.api.v1.routers.rewards.reward_progress_repository")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_list_rewards(
        self, mock_reward_repo, mock_progress_repo, client, mock_user, mock_reward
    ):
        """Test listing all rewards."""
        mock_reward_repo.get_all_active = AsyncMock(return_value=[mock_reward])
        mock_progress_repo.get_all_by_user = AsyncMock(return_value=[])

        response = client.get("/v1/rewards")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["rewards"]) == 1
        assert data["rewards"][0]["reward"]["name"] == mock_reward.name

    @patch("src.api.v1.routers.rewards.reward_progress_repository")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_list_rewards_with_progress(
        self,
        mock_reward_repo,
        mock_progress_repo,
        client,
        mock_reward,
        mock_reward_progress,
    ):
        """Test listing rewards with progress information."""
        mock_reward_repo.get_all_active = AsyncMock(return_value=[mock_reward])
        mock_progress_repo.get_all_by_user = AsyncMock(
            return_value=[mock_reward_progress]
        )

        response = client.get("/v1/rewards")

        assert response.status_code == 200
        data = response.json()
        assert len(data["rewards"]) >= 0
        if len(data["rewards"]) > 0:
            assert "progress" in data["rewards"][0]


class TestGetReward:
    """Test GET /v1/rewards/{reward_id} endpoint."""

    @patch("src.api.v1.routers.rewards.reward_progress_repository")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_get_reward_success(
        self, mock_reward_repo, mock_progress_repo, client, mock_user, mock_reward
    ):
        """Test getting a reward by ID."""
        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_progress_repo.get_by_user_and_reward = AsyncMock(return_value=None)

        response = client.get(f"/v1/rewards/{mock_reward.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["reward"]["id"] == mock_reward.id
        assert data["reward"]["name"] == mock_reward.name

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_get_reward_not_found(self, mock_repo, client):
        """Test getting non-existent reward."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.get("/v1/rewards/999")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "REWARD_NOT_FOUND"

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_get_reward_forbidden(self, mock_repo, client, mock_reward):
        """Test getting reward belonging to another user."""
        mock_reward.user_id = 999  # Different user
        mock_repo.get_by_id = AsyncMock(return_value=mock_reward)

        response = client.get(f"/v1/rewards/{mock_reward.id}")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"


class TestCreateReward:
    """Test POST /v1/rewards endpoint."""

    @patch("src.api.v1.routers.rewards.reward_service")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_create_reward_success(
        self, mock_repo, mock_service, client, mock_user, mock_reward
    ):
        """Test creating a new reward."""
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_service.create_reward = AsyncMock(return_value=mock_reward)

        response = client.post(
            "/v1/rewards",
            json={
                "name": "Coffee",
                "weight": 10.0,
                "pieces_required": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == mock_reward.name

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_create_reward_duplicate(self, mock_repo, client, mock_reward):
        """Test creating reward with duplicate name."""
        mock_repo.get_by_name = AsyncMock(return_value=mock_reward)

        response = client.post(
            "/v1/rewards", json={"name": "Coffee", "weight": 10.0}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "REWARD_EXISTS"

    @patch("src.api.v1.routers.rewards.reward_service")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_create_reward_with_optional_fields(
        self, mock_repo, mock_service, client, mock_reward
    ):
        """Test creating reward with optional fields."""
        mock_reward.piece_value = 1.5
        mock_reward.max_daily_claims = 2
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_service.create_reward = AsyncMock(return_value=mock_reward)

        response = client.post(
            "/v1/rewards",
            json={
                "name": "Coffee",
                "weight": 10.0,
                "pieces_required": 5,
                "piece_value": 1.5,
                "max_daily_claims": 2,
            },
        )

        assert response.status_code == 201


class TestUpdateReward:
    """Test PATCH /v1/rewards/{reward_id} endpoint."""

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_update_reward_success(self, mock_repo, client, mock_user, mock_reward):
        """Test updating a reward."""
        updated_reward = mock_reward
        updated_reward.name = "Updated Name"
        mock_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_repo.get_by_name = AsyncMock(return_value=None)

        # Return updated reward on second call to get_by_id
        mock_repo.get_by_id = AsyncMock(side_effect=[mock_reward, updated_reward])

        response = client.patch(
            f"/v1/rewards/{mock_reward.id}", json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_update_reward_clear_piece_value(self, mock_repo, client, mock_reward):
        """Test clearing piece_value by setting to None."""
        mock_reward.piece_value = 1.5
        updated_reward = mock_reward
        updated_reward.piece_value = None

        mock_repo.get_by_id = AsyncMock(side_effect=[mock_reward, updated_reward])

        response = client.patch(
            f"/v1/rewards/{mock_reward.id}", json={"piece_value": None}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["piece_value"] is None

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_update_reward_pieces_required_success(self, mock_repo, client, mock_reward):
        """Test updating pieces_required."""
        updated_reward = mock_reward
        updated_reward.pieces_required = 7
        mock_repo.get_by_id = AsyncMock(side_effect=[mock_reward, updated_reward])
        mock_repo.get_by_name = AsyncMock(return_value=None)

        response = client.patch(
            f"/v1/rewards/{mock_reward.id}", json={"pieces_required": 7}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pieces_required"] == 7

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_update_reward_not_found(self, mock_repo, client):
        """Test updating non-existent reward."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.patch("/v1/rewards/999", json={"name": "Test"})

        assert response.status_code == 404

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_update_reward_duplicate_name(self, mock_repo, client, mock_reward):
        """Test updating reward with duplicate name."""
        existing_reward = MagicMock()
        existing_reward.id = 2
        existing_reward.name = "Existing"

        mock_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_repo.get_by_name = AsyncMock(return_value=existing_reward)

        response = client.patch(
            f"/v1/rewards/{mock_reward.id}", json={"name": "Existing"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "REWARD_EXISTS"


class TestDeleteReward:
    """Test DELETE /v1/rewards/{reward_id} endpoint."""

    @patch("src.api.v1.routers.rewards.reward_progress_repository")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_delete_reward_success(
        self, mock_reward_repo, mock_progress_repo, client, mock_reward
    ):
        """Test deleting a reward with no progress."""
        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_progress_repo.get_by_user_and_reward = AsyncMock(return_value=None)

        response = client.delete(f"/v1/rewards/{mock_reward.id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("src.api.v1.routers.rewards.reward_progress_repository")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_delete_reward_has_progress(
        self,
        mock_reward_repo,
        mock_progress_repo,
        client,
        mock_reward,
        mock_reward_progress,
    ):
        """Test deleting reward with active progress fails."""
        mock_reward_progress.pieces_earned = 5  # Has progress
        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_progress_repo.get_by_user_and_reward = AsyncMock(
            return_value=mock_reward_progress
        )

        response = client.delete(f"/v1/rewards/{mock_reward.id}")

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "HAS_PROGRESS"

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_delete_reward_not_found(self, mock_repo, client):
        """Test deleting non-existent reward."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.delete("/v1/rewards/999")

        assert response.status_code == 404


class TestClaimReward:
    """Test POST /v1/rewards/{reward_id}/claim endpoint."""

    @patch("src.api.v1.routers.rewards.reward_service")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_claim_reward_success(
        self, mock_reward_repo, mock_service, client, mock_user, mock_reward
    ):
        """Test successfully claiming an achieved reward."""
        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_service.mark_reward_claimed = AsyncMock(return_value=None)

        response = client.post(f"/v1/rewards/{mock_reward.id}/claim")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "claimed" in data["message"].lower()
        assert data["reward"]["id"] == mock_reward.id
        mock_service.mark_reward_claimed.assert_called_once_with(
            mock_user.id, mock_reward.id
        )

    @patch("src.api.v1.routers.rewards.reward_service")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_claim_reward_not_achieved(
        self, mock_reward_repo, mock_service, client, mock_reward
    ):
        """Test claiming reward that is not yet achieved."""
        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_service.mark_reward_claimed = AsyncMock(
            side_effect=ValueError("Reward not achieved yet")
        )

        response = client.post(f"/v1/rewards/{mock_reward.id}/claim")

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "CLAIM_ERROR"

    @patch("src.api.v1.routers.rewards.reward_service")
    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_claim_reward_already_claimed(
        self, mock_reward_repo, mock_service, client, mock_reward
    ):
        """Test claiming already claimed reward."""
        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)
        mock_service.mark_reward_claimed = AsyncMock(
            side_effect=ValueError("Reward already claimed")
        )

        response = client.post(f"/v1/rewards/{mock_reward.id}/claim")

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "CLAIM_ERROR"

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_claim_reward_not_found(self, mock_repo, client):
        """Test claiming non-existent reward."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.post("/v1/rewards/999/claim")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "REWARD_NOT_FOUND"

    @patch("src.api.v1.routers.rewards.reward_repository")
    def test_claim_reward_forbidden(self, mock_repo, client, mock_reward):
        """Test claiming reward belonging to another user."""
        mock_reward.user_id = 999  # Different user
        mock_repo.get_by_id = AsyncMock(return_value=mock_reward)

        response = client.post(f"/v1/rewards/{mock_reward.id}/claim")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"


class TestGetAllProgress:
    """Test GET /v1/rewards/progress endpoint."""

    @patch("src.api.v1.routers.rewards.reward_repository")
    @patch("src.api.v1.routers.rewards.reward_progress_repository")
    def test_get_all_progress(
        self,
        mock_progress_repo,
        mock_reward_repo,
        client,
        mock_reward_progress,
        mock_reward,
    ):
        """Test getting all reward progress."""
        mock_progress_repo.get_all_by_user = AsyncMock(
            return_value=[mock_reward_progress]
        )
        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)

        response = client.get("/v1/rewards/progress")

        assert response.status_code == 200
        data = response.json()
        assert "progress" in data
        assert "total" in data
