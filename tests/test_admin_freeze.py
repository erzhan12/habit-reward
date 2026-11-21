"""Admin freeze controls and the read-only HabitLog admin (feature 0048)."""

from datetime import date

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from src.core.models import Habit, HabitFreezeEvent, HabitLog, User
from src.services.streak_service import StreakService


class AdminFreezeTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_0048", password="test-pass-0048", telegram_id="9900480", name="Admin"
        )
        self.client.force_login(self.admin_user)
        self.owner = User.objects.create_user(
            username="tg_9900481", telegram_id="9900481", name="Owner", language="en"
        )
        self.habit = Habit.objects.create(user=self.owner, name="Walk", weight=10)
        self.log = HabitLog.objects.create(
            user=self.owner, habit=self.habit, streak_count=1, habit_weight=10,
            total_weight_applied=80.0, last_completed_date=date(2026, 11, 16),
        )

    def _action(self, action, habit=None):
        return self.client.post(
            reverse("admin:core_habit_changelist"),
            {"action": action, "_selected_action": [(habit or self.habit).pk]},
            follow=True,
        )

    def _count(self):
        return Habit.objects.get(pk=self.habit.pk).freeze_count

    # --- Grant / Remove ------------------------------------------------------------------

    def test_grant_creates_untracked_freeze_and_invalidates_cache(self):
        cache.set(StreakService.cache_key(self.owner.id), {"stale": True})
        with self.captureOnCommitCallbacks(execute=True):
            response = self._action("grant_freeze")
        self.assertContains(response, "Freeze granted: Walk")
        self.assertEqual(self._count(), 1)
        self.assertFalse(HabitFreezeEvent.objects.filter(habit=self.habit).exists())
        self.assertIsNone(cache.get(StreakService.cache_key(self.owner.id)))

    def test_grant_when_full_is_skipped(self):
        Habit.objects.filter(pk=self.habit.pk).update(freeze_count=1)
        response = self._action("grant_freeze")
        self.assertContains(response, "inventory full")
        self.assertEqual(self._count(), 1)

    def test_remove_forfeits_tracked_freeze(self):
        Habit.objects.filter(pk=self.habit.pk).update(freeze_count=1)
        held = HabitFreezeEvent.objects.create(
            user=self.owner, habit=self.habit, habit_log=self.log, event_type="earned",
            earned_on=date(2026, 11, 16), state="held",
        )
        response = self._action("remove_freeze")
        self.assertContains(response, "Freeze removed: Walk")
        self.assertEqual(self._count(), 0)
        held.refresh_from_db()
        self.assertEqual(held.state, "forfeited")

    def test_remove_untracked_and_remove_when_none(self):
        Habit.objects.filter(pk=self.habit.pk).update(freeze_count=1)
        self._action("remove_freeze")
        self.assertEqual(self._count(), 0)
        response = self._action("remove_freeze")
        self.assertContains(response, "no freeze held")

    # --- HabitAdmin save never writes freeze_count ----------------------------------------

    def test_save_model_does_not_overwrite_freeze_count(self):
        """The form's object holds a stale count; a concurrent spend/grant must survive."""
        from types import SimpleNamespace

        from django.contrib.admin.sites import AdminSite

        from src.core.admin import HabitAdmin

        stale = Habit.objects.get(pk=self.habit.pk)  # freeze_count 0, as loaded by the form
        Habit.objects.filter(pk=self.habit.pk).update(freeze_count=1)  # concurrent grant
        stale.name = "Walk outside"
        HabitAdmin(Habit, AdminSite()).save_model(
            None, stale, SimpleNamespace(changed_data=["name"]), change=True
        )
        habit = Habit.objects.get(pk=self.habit.pk)
        self.assertEqual((habit.name, habit.freeze_count), ("Walk outside", 1))

    def test_change_form_saves_edits(self):
        url = reverse("admin:core_habit_change", args=[self.habit.pk])
        response = self.client.post(url, {
            "user": self.owner.pk, "name": "Walk outside", "weight": 10,
            "category": "", "active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Habit.objects.get(pk=self.habit.pk).name, "Walk outside")

    # --- HabitLog admin is read-only except revert ----------------------------------------

    def test_habitlog_admin_blocks_add_change_delete(self):
        self.assertEqual(self.client.get(reverse("admin:core_habitlog_add")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("admin:core_habitlog_delete", args=[self.log.pk]), {"post": "yes"}).status_code,
            403,
        )
        change = self.client.post(
            reverse("admin:core_habitlog_change", args=[self.log.pk]),
            {"last_completed_date": "2026-11-10"},
        )
        self.assertEqual(change.status_code, 403)
        self.assertEqual(HabitLog.objects.get(pk=self.log.pk).last_completed_date, date(2026, 11, 16))

    def test_habitlog_changelist_has_revert_but_no_delete_action(self):
        response = self.client.get(reverse("admin:core_habitlog_changelist"))
        self.assertEqual(response.status_code, 200)
        actions = dict(response.context["action_form"].fields["action"].choices)
        self.assertIn("revert_selected_logs", actions)
        self.assertNotIn("delete_selected", actions)

    def test_habitlog_change_view_still_viewable(self):
        response = self.client.get(reverse("admin:core_habitlog_change", args=[self.log.pk]))
        self.assertEqual(response.status_code, 200)

    def test_freeze_event_admin_is_read_only(self):
        event = HabitFreezeEvent.objects.create(
            user=self.owner, habit=self.habit, habit_log=self.log, event_type="earned",
            earned_on=date(2026, 11, 16), state="held",
        )
        self.assertEqual(self.client.get(reverse("admin:core_habitfreezeevent_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:core_habitfreezeevent_add")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("admin:core_habitfreezeevent_delete", args=[event.pk]), {"post": "yes"}).status_code,
            403,
        )

    def test_deleting_habit_in_admin_still_cascades(self):
        HabitFreezeEvent.objects.create(
            user=self.owner, habit=self.habit, habit_log=self.log, event_type="earned",
            earned_on=date(2026, 11, 16), state="held",
        )
        response = self.client.post(reverse("admin:core_habit_delete", args=[self.habit.pk]), {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Habit.objects.filter(pk=self.habit.pk).exists())
        self.assertFalse(HabitLog.objects.filter(pk=self.log.pk).exists())
        self.assertFalse(HabitFreezeEvent.objects.filter(habit_id=self.habit.pk).exists())

    def test_deleting_user_in_admin_still_cascades(self):
        response = self.client.post(reverse("admin:core_user_delete", args=[self.owner.pk]), {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(HabitLog.objects.filter(pk=self.log.pk).exists())
