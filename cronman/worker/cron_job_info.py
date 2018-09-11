# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from collections import OrderedDict

from cronman.job import cron_job_registry
from cronman.utils import function_signature


class CronJobClassList(object):
    """Listing cron job classes"""

    def __init__(self, name=None, cron_job_class=None):
        if name or cron_job_class:
            if not name:
                name = cron_job_class.__name__
            elif not cron_job_class:
                cron_job_class = cron_job_registry.get(name)
            items = [(name, cron_job_class)]
        else:
            items = sorted(
                cron_job_registry.items(),
                # Sort by module path, name:
                key=lambda t: (t[1].__module__, t[0]),
            )
        self.items = items

    def _iter_info_items(self):
        """Iterator over information dicts for available cron job classes."""
        for name, cron_job_class in self.items:
            item = OrderedDict()
            item["name"] = name
            item["class"] = "{}.{}".format(
                cron_job_class.__module__, cron_job_class.__name__
            )
            item["_cron_job_class"] = cron_job_class
            yield item

    def summary(self):
        """Retrieves brief information about available cron job classes"""
        items = list(self._iter_info_items())
        totals = {"TOTAL": len(items)}
        return items, totals

    def details(self):
        """Retrieves more information about available cron job classes"""
        items = []
        totals = {"TOTAL": 0}
        for item in self._iter_info_items():
            cron_job_class = item["_cron_job_class"]
            params = function_signature(cron_job_class.run)
            if params:
                item["params"] = params
            description = "\n".join(
                line.strip()
                for line in (cron_job_class.__doc__ or "").split("\n")
            )
            if description:
                item["description"] = "\n" + description
            totals["TOTAL"] += 1
            items.append(item)
        return items, totals
