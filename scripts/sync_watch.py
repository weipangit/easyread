"""start.cmd 用：启动 EasyRead，随即在后台同步一次；运行期间文献库连续一段时间（默认 10 分钟）没有改动、且有没同步的改动时，再同步一次。

python scripts/sync_watch.py <文献库目录> <start.cmd 路径> -- <EasyRead 命令…>
同步时运行 "start.cmd --sync"。
等待时间用环境变量 EASYREAD_SYNC_QUIET（秒）调整。EasyRead 退出后返回它的退出码，退出后的那次同步仍由 start.cmd 做。
"""
import fnmatch
import os
import subprocess
import sys
import time
from pathlib import Path

QUIET = 600
POLL = 30
# 和 start.cmd 里 rclone 的 --exclude 一致：这些文件不同步，改了也不算改动
SKIP = (".easyread-lock.json", ".easyread-probe-*", ".easyread-copy-*")


def snapshot(root: Path) -> frozenset:
    """文献库里每个文件的 (相对路径, 大小, 修改时间)。增删改任何一个文件，结果都会变。"""
    items, stack = [], [root]
    while stack:
        folder = stack.pop()
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for e in entries:
            if any(fnmatch.fnmatch(e.name, p) for p in SKIP):
                continue
            try:
                if e.is_dir(follow_symlinks=False):
                    stack.append(e.path)
                else:
                    st = e.stat(follow_symlinks=False)
                    items.append((os.path.relpath(e.path, root), st.st_size, st.st_mtime_ns))
            except OSError:
                continue
    return frozenset(items)


def log(msg: str):
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def span(seconds: float) -> str:
    return f"{seconds / 60:g} min" if seconds >= 60 else f"{seconds:g} s"


def watch(app, root: Path, sync, quiet: float = QUIET, poll: float = POLL, clock=time.monotonic,
          initial: bool = False) -> int:
    """app 退出前一直盯着文献库；sync() 返回 True 表示同步成功。同步进行时不检查 app，同步完才会返回。
    initial=True 时 app 一启动就先同步一次，失败了按普通改动处理，等一个安静期再试。"""
    synced = last = snapshot(root)
    changed_at = None
    if initial:
        log("Syncing library in the background ...")
        if sync():
            synced = last = snapshot(root)
            log("Sync done.")
        else:
            synced, changed_at = frozenset(), clock()  # 当作有没同步的改动
            log(f"Sync failed, will retry after {span(quiet)} without changes.")
    while True:
        try:
            return app.wait(timeout=poll)
        except subprocess.TimeoutExpired:
            pass
        now = snapshot(root)
        if now != last:
            last, changed_at = now, clock()
        if now == synced or changed_at is None or clock() - changed_at < quiet:
            continue
        log(f"No changes for {span(quiet)}, syncing library ...")
        if sync():
            synced = last = snapshot(root)
            changed_at = None
            log("Sync done.")
        else:
            changed_at = clock()  # 失败了等下一个安静期再试
            log(f"Sync failed, will retry after another {span(quiet)} without changes.")


def main(argv) -> int:
    if len(argv) < 4 or argv[2] != "--":
        print(__doc__, file=sys.stderr)
        return 2
    root, launcher, app_cmd = Path(argv[0]), argv[1], argv[3:]
    sync_cmd = [os.environ.get("ComSpec", "cmd.exe"), "/c", "call", launcher, "--sync"]
    quiet = float(os.environ.get("EASYREAD_SYNC_QUIET") or QUIET)
    app = subprocess.Popen(app_cmd)
    try:
        return watch(app, root, lambda: subprocess.run(sync_cmd).returncode == 0, quiet=quiet, poll=min(POLL, quiet),
                     initial=True)
    except KeyboardInterrupt:
        return app.wait()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
