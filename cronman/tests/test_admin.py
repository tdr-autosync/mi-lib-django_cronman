import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from cronman.admin import CronTaskAdmin
from cronman.models import CronTask

pytestmark = [pytest.mark.django_db]


@pytest.mark.usefixtures("app1")
class TestCronTaskAdmin:
    """ Tests for CronTaskAdmin """

    def test_change_view(self, admin_client):
        """Test if CronTaskAdmin change view can be loaded."""
        url = reverse("admin:cronman_crontask_change")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_changelist_view(self, admin_client):
        """Test if CronTaskAdmin change list view can be loaded."""
        url = reverse("admin:cronman_crontask_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
