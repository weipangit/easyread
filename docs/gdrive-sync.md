# 用 Google Drive 在几台电脑间同步文献库（rclone）

文献库放在本机读写，Google Drive 上存一份副本，用来在电脑之间传递改动：

```
电脑 A 本地库  ⇄  Google Drive: EasyRead/library  ⇄  电脑 B 本地库
     （启动后在后台同步一次 / 10 分钟没改动同步一次 / 退出后同步一次）
```

`start.cmd` 负责同步：装了 rclone、配置了名为 `gdrive` 的远端时，先直接打开 EasyRead，同时在后台双向同步一次，不用等同步完；运行期间文献库有改动、并且之后连续 10 分钟没有新改动时，再同步一次（由 `scripts/sync_watch.py` 每 30 秒检查一次）；EasyRead 关掉后再同步一次。没装 rclone 或没配置远端时，和原来一样直接启动。

和"把文献库迁到 Google Drive 同步文件夹"（设置 → 云文献库）相比，这种做法有几个好处：读写都在本机，速度快；不受 Drive 流式模式"文件只留在云端"的影响；断网时也能打开；打开不用等同步。

## 一次性配置（每台电脑都要做）

### 1. 安装 rclone

```
winget install Rclone.Rclone
```

需要 1.66 或更高版本（用到了 `--conflict-resolve` 和 `--resync-mode`）。

### 2. 创建自己的 Google OAuth 客户端（整个账号只需做一次）

rclone 内置的公用 client_id 是全球用户共用的配额，经常被限流（`Error 403: rateLimitExceeded`），而且 2026 年内会停用，所以要自己建一个。整个过程免费，不需要开通试用，也不需要绑信用卡。

1. 打开 <https://console.cloud.google.com/projectcreate>，新建项目，名字填 `rclone`，确认左上角已切换到这个项目。
2. 打开 <https://console.cloud.google.com/apis/library/drive.googleapis.com>，点 **Enable**，启用 Google Drive API。
3. 打开 <https://console.cloud.google.com/auth/overview>，点 **Get started**，依次填写：
   - App name 填 `rclone`，User support email 选自己的邮箱；
   - Audience 选 **External**；
   - Contact 填自己的邮箱，勾选同意，点 Create。
4. 在左侧的 **Audience → Test users** 里点 **Add users**，把自己的 Gmail 加进去。
5. 打开 <https://console.cloud.google.com/auth/clients>，点 **Create client**：类型选 **Desktop app**，不要勾选 "Use this client for an AI-powered agent"，点 Create，然后下载 `client_secret_….json`。

### 3. 配置 rclone 远端

把 json 里的 `client_id` 和 `client_secret` 填进去：

```
rclone config create gdrive drive scope=drive client_id=<client_id> client_secret=<client_secret>
```

运行后会自动打开浏览器：选择刚才加为测试用户的那个账号。页面提示 "Google hasn't verified this app" 是正常的，点 **Continue** 继续，再允许访问 Drive。

**第二台电脑可以省掉这一步：** 直接把 `%APPDATA%\rclone\rclone.conf` 复制到新电脑的同一位置，复制过去就能用。这个文件里有 Drive 的访问令牌，等同于密码，只能用 U 盘或其他私密渠道传。

## 第一次同步

双击 `start.cmd` 即可。这台电脑第一次同步时，脚本会自动加上 `--resync --resync-mode newer`，把本地和云端合并：两边都有的文件以较新的为准，只有一边有的会复制到另一边。成功后会留下标记文件 `%USERPROFILE%\EasyRead\.rclone-bisync-ready`，以后只做增量同步。

- 第一台电脑：把整个本地库上传。几百 MB 的库可能要一个小时左右，主要看上行网速。
- 新电脑：本地是空的，会把整个库下载下来。

如果想手动做第一次同步（例如不想同时打开 EasyRead），可以运行：

```
rclone mkdir gdrive:EasyRead/library
rclone bisync gdrive:EasyRead/library "%USERPROFILE%\EasyRead\library" --resync --resync-mode newer --resilient --recover --max-lock 5m --conflict-resolve newer --transfers 16 --checkers 16 --fast-list --exclude ".easyread-lock.json" --exclude ".easyread-probe-*" --exclude ".easyread-copy-*/**" -v
```

成功后自己创建上面那个标记文件。

## 新电脑上的完整步骤（可以直接交给 AI 执行）

在新电脑上对 AI 说"按 docs/gdrive-sync.md 把这台新电脑配好"，AI 按下面的步骤操作。人只需要做两件事：提供 `rclone.conf`（或在浏览器里点一次授权），以及提供模型的 API Key。

**给执行的 AI：** 每一步先检查，已经满足就跳过；整个过程可以重复运行。需要人做的事一次问清楚，其余的不要逐步确认。不要把 `rclone.conf`、client_secret、API Key 写进仓库、提交或贴到对话以外的地方。

0. **先问一句：旧电脑上的 EasyRead 关掉了吗，黑窗口同步完了吗？** 没有的话，先让人去关，否则新电脑拿不到最后那次的改动。
1. **代码。** 如果当前目录不是这个仓库，就运行 `git clone https://github.com/weipangit/easyread.git "%USERPROFILE%\easyread"`（人指定了位置就用人指定的），后面的步骤都在仓库目录里执行。
2. **Python 3.10+。** 用 `py -3 --version` 或 `python --version` 检查；没有就运行 `winget install Python.Python.3.12`。
3. **rclone 1.66+。** 用 `rclone version` 检查；没有就运行 `winget install Rclone.Rclone`。刚装完时当前 shell 的 PATH 还没更新，这时用完整路径调用：`%LOCALAPPDATA%\Microsoft\WinGet\Packages\Rclone.Rclone_*\rclone-*\rclone.exe`。
4. **Drive 授权。** 如果 `rclone listremotes` 里已经有 `gdrive:`，就跳过这一步。没有的话，问人选哪种方式：
   - 人给出旧电脑上 `rclone.conf` 的位置（U 盘之类）：复制到 `%APPDATA%\rclone\rclone.conf`；
   - 人给出 client_id 和 client_secret：运行 `rclone config create gdrive drive scope=drive client_id=<…> client_secret=<…>`，提醒人在弹出的浏览器里选自己的 Gmail，看到 "Google hasn't verified this app" 时点 Continue。

   做完后，用 `rclone lsd gdrive:EasyRead` 确认能看到 `library`。
5. **Python 环境。** 如果没有 `.venv\Scripts\pythonw.exe`，就运行 `py -3 -m venv .venv`（没有 `py` 就用 `python`），再运行 `.venv\Scripts\python.exe -m pip install -q -e .`。
6. **第一次同步。** 如果 `%USERPROFILE%\EasyRead\.rclone-bisync-ready` 已经存在，就跳过。否则在后台运行上面"第一次同步"里那条手动 `rclone bisync … --resync …` 命令（库大的话要很久，不要因为超时中断），成功后创建这个标记文件。失败时看输出，对照下面的排错表处理。
7. **核对。** 运行 `rclone size gdrive:EasyRead/library` 和 `rclone size "%USERPROFILE%\EasyRead\library"`，两边的文件数应该一致（只差排除掉的那几种文件）。
8. **桌面快捷方式。** 在桌面建一个名为 `EasyRead` 的快捷方式，指向仓库里的 `start.cmd`，起始位置设为仓库目录。以后只用这个快捷方式启动。
9. **模型和 API Key。** 这些在 `%USERPROFILE%\EasyRead\config.json` 里，不会同步。问人：是要从旧电脑复制 `config.json`（两台电脑用户名相同时可以直接用），还是打开 EasyRead 后在设置里重新填。
10. **收尾。** 告诉人：已经配好了，双击桌面上的 `EasyRead` 就能用；任务栏里最小化的 `EasyRead sync` 窗口不要关；不要两台电脑同时开着 EasyRead。

## 日常使用规则

- **只用 `start.cmd` 启动。** 用 `easyread.exe` 或安装版启动不会同步。如果用了它们，关掉之后运行一次 `start.cmd --sync`，把改动推上去。
- **同步窗口会最小化在任务栏里（标题是 `EasyRead sync`），不要关掉它。** 关掉 EasyRead 后，它会做最后一次同步，然后自行关闭；最后那次同步失败时，它会停在任务栏里等你看提示。
- **不要在两台电脑上同时开着 EasyRead。** 正确的顺序是：在 A 上关掉，等同步完成，再到 B 上打开。
- **刚从另一台电脑换过来时**，另一台电脑的改动要等后台那次同步完成（任务栏里的 `EasyRead sync` 窗口显示 `Sync done.`）才会到本机，之后在文献库里刷新一下就能看到。
- 后台同步失败时窗口里会提示，等 10 分钟没有改动后自动重试，不影响使用；退出后同步失败时窗口会暂停，改动留在本地，下次启动会补上。

## 细节和排错

| 情况 | 说明 |
|---|---|
| 同步哪个目录 | 只同步 `%USERPROFILE%\EasyRead\library`（`start.cmd` 设置了 `EASYREAD_HOME=%USERPROFILE%\EasyRead`）。如果在"设置 → 云文献库"里把库迁到了别处，要先迁回来。 |
| 换远端或路径 | 运行 `start.cmd` 前设置环境变量 `EASYREAD_REMOTE`，例如 `mydrive:Papers/library`。 |
| 运行中多久同步一次 | 文献库最后一次改动后安静满 10 分钟就同步，一直在改就一直等；没有新改动不会同步。想改等待时间，运行 `start.cmd` 前设置环境变量 `EASYREAD_SYNC_QUIET`（秒），例如 `300`。运行中的同步失败会在窗口里提示，再等一个安静期重试，不会暂停。 |
| 手动同步一次 | 运行 `start.cmd --sync`，只同步，不打开 EasyRead。 |
| 不同步的文件 | `.easyread-lock.json`（设备心跳）、`.easyread-probe-*`（写入探测）、`.easyread-copy-*/`（迁移临时目录）。 |
| 冲突 | `--conflict-resolve newer`：两边都改过的文件保留较新的。 |
| 同步中途被打断 | 锁文件 5 分钟后自动失效（`--max-lock 5m`），下次运行会自动恢复（`--recover`）。已经传完的文件不会重传。 |
| `403 rateLimitExceeded` | 用的还是 rclone 的公用 client_id，按上面的第 2、3 步换成自己的。 |
| 提示 `prior lock file found` | 确认没有 rclone 进程在运行后，删掉 `%LOCALAPPDATA%\rclone\bisync\*.lck`。 |
| 想重新做一次初始同步 | 删掉 `%USERPROFILE%\EasyRead\.rclone-bisync-ready`，下次启动会再做一次 `--resync`。 |
| 大量上传时电脑睡眠 | 锁屏不影响同步，睡眠或合盖会中断。中断后重新运行即可。 |
