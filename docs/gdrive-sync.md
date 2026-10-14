# 用 Google Drive 在几台电脑间同步文献库（rclone）

文献库放在本机读写，Google Drive 上存一份副本，用来在电脑之间传递改动：

```
电脑 A 本地库  ⇄  Google Drive: EasyRead/library  ⇄  电脑 B 本地库
           （启动前拉一次 / 退出后推一次）
```

`start.cmd` 负责同步：装了 rclone、配置了名为 `gdrive` 的远端时，启动 EasyRead 前先双向同步一次，EasyRead 关掉后再同步一次。没装 rclone 或没配置远端时，和原来一样直接启动。

和"把文献库迁到 Google Drive 同步文件夹"（设置 → 云文献库）相比，这种做法有几个好处：读写都在本机，速度快；不受 Drive 流式模式"文件只留在云端"的影响；断网时也能打开；同步时机明确，开始用之前一定已经拿到最新内容。

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

## 新电脑上的完整步骤

1. 获取代码（包含同步功能的 `start.cmd`），安装 Python 3.10+（勾选 "Add python.exe to PATH"）。
2. `winget install Rclone.Rclone`。
3. 复制 `rclone.conf`，或者按上面的第 3 步重新授权。
4. 双击 `start.cmd`：自动建好 Python 环境，下载整个文献库，然后打开 EasyRead。
5. 在设置里重新填写模型和 API Key。这些在 `config.json` 里，不在 `library` 里，不会同步。如果两台电脑的用户名相同，也可以直接复制 `%USERPROFILE%\EasyRead\config.json`。

## 日常使用规则

- **只用 `start.cmd` 启动。** 用 `easyread.exe` 或安装版启动不会同步。如果用了它们，关掉之后再双击一次 `start.cmd`、然后关掉，把改动推上去。
- **EasyRead 运行时，黑窗口要一直开着。** 关掉 EasyRead 后，窗口会做最后一次同步，然后自行关闭。
- **不要在两台电脑上同时开着 EasyRead。** 正确的顺序是：在 A 上关掉，等同步完成，再到 B 上打开。
- 同步失败时窗口会暂停并给出提示。启动前同步失败时，用本地库照常打开；退出后同步失败时，改动留在本地，下次启动会补上。

## 细节和排错

| 情况 | 说明 |
|---|---|
| 同步哪个目录 | 只同步 `%USERPROFILE%\EasyRead\library`（`start.cmd` 设置了 `EASYREAD_HOME=%USERPROFILE%\EasyRead`）。如果在"设置 → 云文献库"里把库迁到了别处，要先迁回来。 |
| 换远端或路径 | 运行 `start.cmd` 前设置环境变量 `EASYREAD_REMOTE`，例如 `mydrive:Papers/library`。 |
| 不同步的文件 | `.easyread-lock.json`（设备心跳）、`.easyread-probe-*`（写入探测）、`.easyread-copy-*/`（迁移临时目录）。 |
| 冲突 | `--conflict-resolve newer`：两边都改过的文件保留较新的。 |
| 同步中途被打断 | 锁文件 5 分钟后自动失效（`--max-lock 5m`），下次运行会自动恢复（`--recover`）。已经传完的文件不会重传。 |
| `403 rateLimitExceeded` | 用的还是 rclone 的公用 client_id，按上面的第 2、3 步换成自己的。 |
| 提示 `prior lock file found` | 确认没有 rclone 进程在运行后，删掉 `%LOCALAPPDATA%\rclone\bisync\*.lck`。 |
| 想重新做一次初始同步 | 删掉 `%USERPROFILE%\EasyRead\.rclone-bisync-ready`，下次启动会再做一次 `--resync`。 |
| 大量上传时电脑睡眠 | 锁屏不影响同步，睡眠或合盖会中断。中断后重新运行即可。 |
