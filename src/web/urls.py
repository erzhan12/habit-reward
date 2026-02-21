"""Web interface URL patterns."""

from django.urls import path

from src.web.views.dashboard import complete_habit, dashboard, revert_habit
from src.web.views.history import history_page
from src.web.views.rewards import claim_reward, rewards_page
from src.web.views.streaks import streaks_page

urlpatterns = [
    path("", dashboard, name="web_dashboard"),
    path("streaks/", streaks_page, name="web_streaks"),
    path("history/", history_page, name="web_history"),
    path("rewards/", rewards_page, name="web_rewards"),
    path("habits/<int:habit_id>/complete/", complete_habit, name="web_complete_habit"),
    path("habits/<int:habit_id>/revert/", revert_habit, name="web_revert_habit"),
    path("rewards/<int:reward_id>/claim/", claim_reward, name="web_claim_reward"),
]
