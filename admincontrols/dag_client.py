"""
Placeholder for the bank-rates extraction DAG controller.

The UI already calls every method here. Until you connect it, each action reports
"not connected". To connect later, implement the methods below (for Apache Airflow
this is the stable REST API: /api/v1/dags/{dag_id}, /dagRuns, PATCH is_paused, ...)
and return the same shapes.
"""


class NotConnected(Exception):
    pass


class DagClient:
    dag_id = "bank_rates_extraction"

    def status(self):
        """-> {"connected": bool, "state": "running|idle|paused|failed|unknown",
                "paused": bool|None, "schedule": str|None, "next_run": str|None,
                "last_run": str|None}"""
        return {"connected": False, "state": "unknown", "paused": None,
                "schedule": None, "next_run": None, "last_run": None}

    def recent_runs(self, limit=10):
        """-> [{"run_id": str, "state": str, "started": str, "ended": str|None, "trigger": str}]"""
        return []

    def trigger(self, conf=None):
        raise NotConnected

    def pause(self):
        raise NotConnected

    def resume(self):
        raise NotConnected

    def set_schedule(self, cron):
        raise NotConnected


dag = DagClient()
