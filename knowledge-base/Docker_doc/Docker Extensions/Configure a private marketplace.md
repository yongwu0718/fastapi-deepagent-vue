# 为扩展配置私有市场（private marketplace）

了解如何为您的 Docker Desktop 用户配置和设置一个包含精选扩展列表的私有市场。

Docker Extensions 的私有市场（private marketplace）专为不为开发人员提供机器 root 权限的组织设计。它利用[设置管理（Settings Management）](/enterprise/security/hardened-desktop/settings-management/)，使管理员能够完全控制私有市场。

## 前提条件（Prerequisites）

- [下载并安装 Docker Desktop](https://docs.docker.com/desktop/release-notes/)。
- 您必须是组织的管理员。
- 您能够通过设备管理软件（例如 [Jamf](https://www.jamf.com/)）将 `extension-marketplace` 文件夹和 `admin-settings.json` 文件推送到下面指定的位置。

## 第一步：初始化私有市场

1. 在本地创建一个文件夹，用于存放将部署到开发人员机器上的内容：

   ```console
   $ mkdir my-marketplace
   $ cd my-marketplace
   ```

2. 为您的市场初始化配置文件：

   **Mac**

   ```console
   $ /Applications/Docker.app/Contents/Resources/bin/extension-admin init
   ```

   **Windows**

   ```console
   # 对于所有用户安装
   $ C:\Program Files\Docker\Docker\resources\bin\extension-admin init

   # 对于每用户安装
   $ %LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\extension-admin init
   ```

   **Linux**

   ```console
   $ /opt/docker-desktop/extension-admin init
   ```

这将创建 2 个文件：

- `admin-settings.json`，一旦应用到开发人员的 Docker Desktop 上，将激活私有市场功能。
- `extensions.txt`，决定在您的私有市场中列出哪些扩展。

> [!IMPORTANT]
>
> 如果您的组织正在通过[管理控制台（Admin Console）](/extensions/private-marketplace/enterprise/security/hardened-desktop/settings-management/configure-admin-console/)使用[设置管理（Settings Management）](/enterprise/security/hardened-desktop/settings-management/)，则您不需要 `admins-settings.json` 文件。请删除生成的文件，仅保留 `extensions.txt` 文件。

## 第二步：设置行为

生成的 `admin-settings.json` 文件包含您可以修改的各种设置。

> [!IMPORTANT]
>
> 如果您的组织正在通过[管理控制台（Admin Console）](/extensions/private-marketplace/enterprise/security/hardened-desktop/settings-management/configure-admin-console/)管理设置，您将在管理控制台中定义相同的设置，而不是在 `admin-settings.json` 文件中。

每个设置都有一个 `value` 可供设置，还包括一个 `locked` 字段，允许您锁定该设置，使其对开发人员不可更改。

- `extensionsEnabled`：启用 Docker Extensions。
- `extensionsPrivateMarketplace`：激活私有市场，并确保 Docker Desktop 连接到由管理员定义和控制的内容，而不是公共 Docker 市场。
- `onlyMarketplaceExtensions`：允许或阻止开发人员使用命令行安装其他扩展。正在开发新扩展的团队必须将此设置解锁（`"locked": false`），才能安装和测试正在开发的扩展。
- `extensionsPrivateMarketplaceAdminContactURL`：定义一个联系链接，供开发人员在私有市场中请求新扩展。如果 `value` 为空，则在 Docker Desktop 上不会向开发人员显示任何链接；否则，可以是 HTTP 链接或 “mailto:” 链接。例如，

  ```json
  "extensionsPrivateMarketplaceAdminContactURL": {
    "locked": true,
    "value": "mailto:admin@acme.com"
  }
  ```

要了解有关 `admin-settings.json` 文件的更多信息，请参阅[设置管理（Settings Management）](/enterprise/security/hardened-desktop/settings-management/)。

## 第三步：列出允许的扩展

生成的 `extensions.txt` 文件定义了私有市场中可用的扩展列表。

文件中的每一行是一个允许的扩展，格式为 `org/repo:tag`。

例如，如果您希望允许 Disk Usage 扩展，您需要在 `extensions.txt` 文件中输入以下内容：

```console
docker/disk-usage-extension:0.2.8
```

如果未提供 tag，则使用该 image 可用的最新 tag。您也可以用 `#` 注释掉某些行，从而忽略该扩展。

此列表可以包含不同类型的扩展镜像（extension images）：

- 来自公共市场或存储在 Docker Hub 中的任何公共镜像的扩展。
- 作为私有镜像存储在 Docker Hub 中的扩展镜像。开发人员需要登录并具有对这些镜像的拉取访问权限。
- 存储在私有 registry 中的扩展镜像。开发人员需要登录并具有对这些镜像的拉取访问权限。

> [!IMPORTANT]
>
> 您的开发人员只能安装您列出的版本的扩展。

## 第四步：生成私有市场

一旦 `extensions.txt` 中的列表准备就绪，您就可以生成市场：

**Mac**

```console
$ /Applications/Docker.app/Contents/Resources/bin/extension-admin generate
```

**Windows**

```console
# 对于所有用户安装
$ C:\Program Files\Docker\Docker\resources\bin\extension-admin generate

# 对于每用户安装
$ %LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\extension-admin generate
```

**Linux**

```console
$ /opt/docker-desktop/extension-admin generate
```

这将创建一个 `extension-marketplace` 目录，并下载所有允许扩展的市场元数据。

市场内容是根据扩展镜像信息（如镜像标签）生成的，该格式[与公共扩展相同](/extensions/private-marketplace/extensions-sdk/extensions/labels/)。它包括扩展标题、描述、屏幕截图、链接等。

## 第五步：测试私有市场设置

建议您在您的 Docker Desktop 安装上尝试私有市场。

1. 在终端中运行以下命令。该命令会自动将生成的文件复制到 Docker Desktop 读取配置文件的位置。根据您的操作系统，该位置为：

    - Mac：`/Library/Application\ Support/com.docker.docker`
    - Windows：`C:\ProgramData\DockerDesktop`
    - Linux：`/usr/share/docker-desktop`

   **Mac**

   ```console
   $ sudo /Applications/Docker.app/Contents/Resources/bin/extension-admin apply
   ```

   **Windows（以管理员身份运行）**

   ```console
   # 对于所有用户安装
   $ C:\Program Files\Docker\Docker\resources\bin\extension-admin apply

   # 对于每用户安装
   $ %LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\extension-admin apply
   ```

   **Linux**

   ```console
   $ sudo /opt/docker-desktop/extension-admin apply
   ```

2. 退出并重新打开 Docker Desktop。
3. 使用 Docker 账户登录。

> [!IMPORTANT]
>
> 如果您的组织正在通过[管理控制台（Admin Console）](/extensions/private-marketplace/enterprise/security/hardened-desktop/settings-management/configure-admin-console/)管理设置，在 Docker Desktop 4.59 及更早版本中，您必须在步骤 2 之前手动删除 `apply` 命令在目标文件夹中创建的 `admin-settings.json` 文件。在 Docker Desktop 4.60 及更高版本中，不再需要此步骤。

当您选择 **Extensions** 选项卡时，您应该看到私有市场仅列出您在 `extensions.txt` 中允许的扩展。

![Extensions Private Marketplace](/assets/images/extensions-private-marketplace.webp)

## 第六步：分发私有市场

一旦您确认私有市场配置有效，最后一步是使用您组织使用的 MDM 软件（例如 [Jamf](https://www.jamf.com/)）将文件分发到开发人员的机器上。

要分发的文件包括：
* `admin-settings.json`（除非您的组织通过[管理控制台（Admin Console）](/extensions/private-marketplace/enterprise/security/hardened-desktop/settings-management/configure-admin-console/)管理设置）
* 整个 `extension-marketplace` 文件夹及其子文件夹

这些文件必须放置在开发人员的机器上。根据您的操作系统，目标位置为（如上所述）：

- Mac：`/Library/Application\ Support/com.docker.docker`
- Windows：`C:\ProgramData\DockerDesktop`
- Linux：`/usr/share/docker-desktop`

确保您的开发人员已登录 Docker Desktop，以便私有市场配置生效。作为管理员，您应[强制登录（enforce sign-in）](/enterprise/security/enforce-sign-in/)。

## 反馈

如有反馈或发现任何错误，请通过电子邮件发送至 `extensions@docker.com`。