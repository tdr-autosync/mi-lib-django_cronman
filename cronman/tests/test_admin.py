from django.urls import reverse

from cronman.tests.base import BaseCronTestCase


class TestCronTaskAdmin(BaseCronTestCase):
    """ Tests for CronTaskAdmin """

    def test_change_view(self):
        """Test if CronTaskAdmin change view can be loaded."""
        url = reverse("admin:cronman_crontask_change")
        response = self.admin_client().get(url)

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
