"""Tests for rewards views."""

from unittest.mock import AsyncMock, MagicMock, patch

from tests.web.conftest import _mock_progress


class TestRewards:
    """Rewards view tests."""

    @patch("src.web.views.rewards.reward_service")
    def test_rewards_returns_200(self, mock_rs, auth_client):
        mock_rs.get_user_reward_progress.return_value = []
        mock_rs.get_claimed_one_time_rewards.return_value = []
        response = auth_client.get("/rewards/")
        assert response.status_code == 200

    @patch("src.web.views.rewards.reward_service")
    def test_rewards_with_progress(self, mock_rs, auth_client):
        progress = _mock_progress(status_name="PENDING")
        mock_rs.get_user_reward_progress.return_value = [progress]
        mock_rs.get_claimed_one_time_rewards.return_value = []
        response = auth_client.get("/rewards/")
        assert response.status_code == 200

    @patch("src.web.views.rewards.reward_service")
    def test_rewards_status_uses_name(self, mock_rs, auth_client):
        """Verify status is sent as .name (ACHIEVED) not .value (emoji)."""
        progress = _mock_progress(status_name="ACHIEVED")
        mock_rs.get_user_reward_progress.return_value = [progress]
        mock_rs.get_claimed_one_time_rewards.return_value = []
        response = auth_client.get("/rewards/")
        assert response.status_code == 200
        progress.get_status.assert_called()

    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_reward_redirects(self, mock_rs, mock_repo, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id = AsyncMock(return_value=reward)
        mock_rs.mark_reward_claimed.return_value = MagicMock()
        response = auth_client.post("/rewards/1/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"

    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_nonexistent_reward_redirects(self, mock_rs, mock_repo, auth_client):
        mock_repo.get_by_id = AsyncMock(return_value=None)
        response = auth_client.post("/rewards/99999/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"
        mock_rs.mark_reward_claimed.assert_not_called()

    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_failure_still_redirects(self, mock_rs, mock_repo, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id = AsyncMock(return_value=reward)
        mock_rs.mark_reward_claimed.side_effect = ValueError("Not achieved")
        response = auth_client.post("/rewards/1/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"
