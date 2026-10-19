"""start.cmd 的定时同步：文献库安静一段时间且有新改动才同步。  python -m unittest tests.app.test_sync_watch"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sync_watch", ROOT / "scripts" / "sync_watch.py")
sync_watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_watch)


class FakeApp:
    """每次 wait 让时钟走 timeout 秒并执行一步操作；步骤用完就当 EasyRead 退出了。"""

    def __init__(self, clock, steps):
        self.clock, self.steps = clock, list(steps)

    def wait(self, timeout):
        self.clock.t += timeout
        if not self.steps:
            return 0
        step = self.steps.pop(0)
        if step:
            step()
        raise subprocess.TimeoutExpired("easyread", timeout)


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


class SyncWatchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "paper-a").mkdir()
        (self.root / "paper-a" / "meta.json").write_text("{}", encoding="utf-8")
        self.clock = Clock()
        self.synced_at = []

    def run_watch(self, steps, ok=True):
        def sync():
            self.synced_at.append(self.clock.t)
            return ok
        app = FakeApp(self.clock, steps)
        return sync_watch.watch(app, self.root, sync, quiet=600, poll=30, clock=self.clock)

    def write(self, name, text="x"):
        def step():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return step

    def test_no_changes_never_syncs(self):
        self.assertEqual(self.run_watch([None] * 40), 0)
        self.assertEqual(self.synced_at, [])

    def test_syncs_once_after_quiet_period(self):
        self.run_watch([self.write("paper-b/meta.json")] + [None] * 60)
        # 第 30 秒检测到改动，安静满 600 秒后的那次检查同步，之后没有新改动不再同步
        self.assertEqual(self.synced_at, [630.0])

    def test_keeps_waiting_while_changes_continue(self):
        steps = [self.write("paper-a/progress.json", str(i)) for i in range(30)] + [None] * 25
        self.run_watch(steps)
        # 最后一次改动在第 900 秒，安静满 600 秒才同步
        self.assertEqual(self.synced_at, [1500.0])

    def test_skipped_files_do_not_count(self):
        steps = [self.write(".easyread-lock.json", str(i)) for i in range(5)]
        steps += [self.write(".easyread-probe-1"), self.write(".easyread-copy-1/a.json")] + [None] * 30
        self.run_watch(steps)
        self.assertEqual(self.synced_at, [])

    def test_change_reverted_before_quiet_period_does_not_sync(self):
        def remove():
            (self.root / "paper-b.json").unlink()
        self.run_watch([self.write("paper-b.json"), remove] + [None] * 30)
        self.assertEqual(self.synced_at, [])

    def test_failed_sync_retries_after_another_quiet_period(self):
        self.run_watch([self.write("paper-b/meta.json")] + [None] * 50, ok=False)
        self.assertEqual(self.synced_at, [630.0, 1230.0])

    def test_returns_app_exit_code(self):
        app = FakeApp(self.clock, [])
        app.wait = lambda timeout: 3
        self.assertEqual(sync_watch.watch(app, self.root, lambda: True), 3)


if __name__ == "__main__":
    unittest.main()
