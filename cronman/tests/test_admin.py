import datetime

from django.urls import reverse
from django.utils import timezone

from cronman.models import CronTask
from cronman.tests.base import BaseCronTestCase


class TestCronTaskAdmin(BaseCronTestCase):
    """ Tests for CronTaskAdmin """

    def test_change_view(self):
        """Test if CronTaskAdmin change view can be loaded."""
        # Started Task:
        # pid_s1 = 1001
        cron_task = CronTask.objects.run_now(
            "Sleep", now=timezone.now() - datetime.timedelta(minutes=6)
        )[0]

        url = reverse("admin:cronman_crontask_change", args=[cron_task.id])
        print(f"=====> {url}")
        response = self.admin_client().get(url)
        print(f"=====> {response}")


        self.assertEqual(response.status_code, 200)

        loaded_template = response.templates[0]

        self.assertEqual(
            loaded_template.name,
            "cronman/admin/cron_task/change_form.html"
        )

    def test_changelist_view(self):
        """Test if CronTaskAdmin change list view can be loaded."""
        url = reverse("admin:cronman_crontask_changelist")
        response = self.admin_client().get(url)

        self.assertEqual(response.status_code, 200)

        loaded_template = response.templates[0]

        self.assertEqual(
            loaded_template.name,
            "cronman/admin/cron_task/change_list.html"
        )
