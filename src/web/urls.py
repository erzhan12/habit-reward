"""Web interface URL patterns."""

from django.urls import path

from src.web.views.analytics import analytics_page
from src.web.views.dashboard import complete_habit, dashboard, revert_habit
from src.web.views.history import history_page
from src.web.views.rewards import claim_reward, rewards_page
from src.web.views.streaks import streaks_page
from src.web.views.theme import save_theme, theme_page

urlpatterns = [
    path("", dashboard, name="web_dashboard"),
    path("streaks/", streaks_page, name="web_streaks"),
    path("history/", history_page, name="web_history"),
    path("rewards/", rewards_page, name="web_rewards"),
    path("analytics/", analytics_page, name="web_analytics"),
    path("theme/", theme_page, name="web_theme"),
    path("theme/save/", save_theme, name="web_save_theme"),
    path("habits/<int:habit_id>/complete/", complete_habit, name="web_complete_habit"),
    path("habits/<int:habit_id>/revert/", revert_habit, name="web_revert_habit"),
    path("rewards/<int:reward_id>/claim/", claim_reward, name="web_claim_reward"),
]
