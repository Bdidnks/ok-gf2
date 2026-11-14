"""Daily completion persists only confirmed results and expires at game reset."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.tasks.DailyTaskRunner import DailyTaskRunner
from src.tasks.daily_completion import DailyCompletionStore
from tests.TestDailyTaskRunner import ALL_ON, StubTask, build_plan

TEST_TMP_ROOT = Path(__file__).resolve().parent.parent


class TestDailyCompletion(unittest.TestCase):
    def test_second_launch_skips_confirmed_tasks_but_not_farming(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as directory:
            path = Path(directory) / "completion.json"
            clock = lambda: datetime(2026, 11, 14, 18)
            first = StubTask(dict(ALL_ON))
            DailyTaskRunner(first, build_plan(first, {"邮件": "待核查", "竞技场": False}),
                            completion_store=DailyCompletionStore(path, now=clock)).run()
            second = StubTask(dict(ALL_ON))
            runner = DailyTaskRunner(second, build_plan(second, {}),
                                     completion_store=DailyCompletionStore(path, now=clock))
            runner.run()
            executed = [name for kind, name in second.calls if kind == "run"]
            self.assertEqual(executed, ["ensure_main", "邮件", "自动刷体力", "竞技场"])
            self.assertEqual(runner.task_status["skipped"], ["社区每日"])
            self.assertEqual(set(json.loads(path.read_text(encoding="utf-8"))["accounts"]["single_account"]),
                             {"社区每日", "邮件", "竞技场"})

    def test_completion_expires_only_after_reset_and_is_per_account(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as directory:
            path = Path(directory) / "completion.json"
            before = DailyCompletionStore(path, reset_hour=5, now=lambda: datetime(2026, 11, 15, 4, 59))
            before.mark_completed("account_a", "邮件")
            self.assertTrue(before.is_completed("account_a", "邮件"))
            self.assertFalse(before.is_completed("account_b", "邮件"))
            after = DailyCompletionStore(path, reset_hour=5, now=lambda: datetime(2026, 11, 15, 5))
            self.assertFalse(after.is_completed("account_a", "邮件"))

    def test_bad_store_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as directory:
            path = Path(directory) / "completion.json"
            path.write_text("{broken", encoding="utf-8")
            task = StubTask(dict(ALL_ON))
            runner = DailyTaskRunner(task, build_plan(task, {}),
                                     completion_store=DailyCompletionStore(path))
            runner.run()
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")
            self.assertTrue(any("每日完成记录失败" in message for message, _ in task.logs))


if __name__ == "__main__":
    unittest.main()
