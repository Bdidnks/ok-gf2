"""Persist confirmed daily-task completions across application runs."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class DailyCompletionStore:
    def __init__(self, path, reset_hour=5, now=None):
        self.path = Path(path)
        self.reset_hour = int(reset_hour)
        if not 0 <= self.reset_hour <= 23:
            raise ValueError("每日重置小时必须在 0 至 23 之间")
        self.now = now or datetime.now

    def day_key(self):
        """Use the local game day, which starts at the configured reset hour."""
        return (self.now() - timedelta(hours=self.reset_hour)).date().isoformat()

    def _load(self):
        if not self.path.exists():
            return {"day": self.day_key(), "accounts": {}}
        with self.path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or not isinstance(data.get("accounts"), dict):
            raise ValueError("每日完成记录格式无效")
        if data.get("day") != self.day_key():
            return {"day": self.day_key(), "accounts": {}}
        return data

    @staticmethod
    def _account_key(account_id):
        return str(account_id or "single_account")

    def is_completed(self, account_id, task_key):
        items = self._load()["accounts"].get(self._account_key(account_id), [])
        if not isinstance(items, list):
            raise ValueError("每日完成记录中的账号数据格式无效")
        return task_key in items

    def mark_completed(self, account_id, task_key):
        data = self._load()
        account = self._account_key(account_id)
        items = data["accounts"].setdefault(account, [])
        if not isinstance(items, list):
            raise ValueError("每日完成记录中的账号数据格式无效")
        if task_key in items:
            return
        items.append(task_key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, self.path)
