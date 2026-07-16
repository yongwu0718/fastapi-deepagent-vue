# 守护进程代理配置（Daemon proxy configuration）

如果您的组织使用代理服务器连接互联网，您可能需要配置 Docker 守护进程以使用该代理服务器。守护进程使用代理服务器访问存储在 Docker Hub 和其他镜像仓库上的镜像，以及访问 Docker Swarm 中的其他节点。

本页介绍如何为 Docker 守护进程配置代理。有关为 Docker CLI 配置代理设置的说明，请参阅[配置 Docker CLI 使用代理服务器](/engine/cli/proxy/)。

> [!IMPORTANT]
> Docker Desktop 会忽略 `daemon.json` 中指定的代理配置。如果您使用 Docker Desktop，可以使用 [Docker Desktop 设置](/desktop/settings-and-maintenance/settings/#proxies)配置代理。

有两种方法可以配置这些设置：

- 通过配置文件或 CLI 标志[配置守护进程](#daemon-configuration)
- 在系统上设置[环境变量](#environment-variables)

直接配置守护进程的优先级高于环境变量。

## 守护进程配置（Daemon configuration）

您可以在 `daemon.json` 文件中配置守护进程的代理行为，或者使用 `dockerd` 命令的 `--http-proxy` 或 `--https-proxy` CLI 标志。推荐使用 `daemon.json` 进行配置。

```json
{
  "proxies": {
    "http-proxy": "http://proxy.example.com:3128",
    "https-proxy": "http://proxy.example.com:3128",
    "no-proxy": "*.test.example.com,.example.org,127.0.0.0/8"
  }
}
```

更改配置文件后，重启守护进程以使代理配置生效：

```console
$ sudo systemctl restart docker
```

## 环境变量（Environment variables）

Docker 守护进程会在其启动环境中检查以下环境变量，以配置 HTTP 或 HTTPS 代理行为：

- `HTTP_PROXY`
- `http_proxy`
- `HTTPS_PROXY`
- `https_proxy`
- `NO_PROXY`
- `no_proxy`

### systemd 单元文件（systemd unit file）

如果您将 Docker 守护进程作为 systemd 服务运行，可以创建一个 systemd 插入文件，为 `docker` 服务设置这些变量。

> **无根模式（rootless mode）的注意事项**
>
> 在[无根模式](/engine/security/rootless/)下运行 Docker 时，systemd 配置文件的位置不同。在无根模式下，Docker 作为用户态 systemd 服务启动，并使用存储在每个用户主目录 `~/.config/systemd/<user>/docker.service.d/` 中的文件。此外，执行 `systemctl` 时必须不带 `sudo` 并带上 `--user` 标志。如果您以无根模式运行 Docker，请选择“无根模式”标签页。

**常规安装（Regular install）**

1. 为 `docker` 服务创建一个 systemd 插入目录：

   ```console
   $ sudo mkdir -p /etc/systemd/system/docker.service.d
   ```

2. 创建一个名为 `/etc/systemd/system/docker.service.d/http-proxy.conf` 的文件，添加 `HTTP_PROXY` 环境变量：

   ```systemd
   [Service]
   Environment="HTTP_PROXY=http://proxy.example.com:3128"
   ```

   要代理 HTTPS 请求，设置 `HTTPS_PROXY` 环境变量：

   ```systemd
   [Service]
   Environment="HTTPS_PROXY=http://proxy.example.com:3128"
   ```

   可以设置多个环境变量；同时设置 HTTP 和 HTTPS 代理：

   ```systemd
   [Service]
   Environment="HTTP_PROXY=http://proxy.example.com:3128"
   Environment="HTTPS_PROXY=http://proxy.example.com:3128"
   ```

   > [!NOTE]
   >
   > 代理值中的特殊字符（如 `#?!()[]{}`）必须使用 `%%` 进行双重转义。例如：
   >
   > ```systemd
   > [Service]
   > Environment="HTTP_PROXY=http://domain%%5Cuser:complex%%23pass@proxy.example.com:3128/"
   > ```

3. 如果您需要联系内部 Docker 镜像仓库而不通过代理，可以通过 `NO_PROXY` 环境变量指定它们。

   `NO_PROXY` 变量指定一个字符串，其中包含应排除在代理之外的主机的逗号分隔值。以下是排除主机时可以指定的选项：
   - IP 地址前缀（`1.2.3.4`）
   - 域名或特殊 DNS 标签（`*`）
   - 域名匹配该名称及其所有子域。前面带点号的 `.` 仅匹配子域。例如，对于 `foo.example.com` 和 `example.com`：
     - `example.com` 匹配 `example.com` 和 `foo.example.com`
     - `.example.com` 仅匹配 `foo.example.com`
   - 单个星号（`*`）表示不应进行任何代理
   - IP 地址前缀（`1.2.3.4:80`）和域名（`foo.example.com:80`）接受字面端口号

   示例：

   ```systemd
   [Service]
   Environment="HTTP_PROXY=http://proxy.example.com:3128"
   Environment="HTTPS_PROXY=http://proxy.example.com:3128"
   Environment="NO_PROXY=localhost,127.0.0.1,docker-registry.example.com,.corp"
   ```

4. 刷新更改并重启 Docker

   ```console
   $ sudo systemctl daemon-reload
   $ sudo systemctl restart docker
   ```

5. 验证配置已加载并与您所做的更改匹配，例如：

   ```console
   $ sudo systemctl show --property=Environment docker

   Environment=HTTP_PROXY=http://proxy.example.com:3128 HTTPS_PROXY=http://proxy.example.com:3128 NO_PROXY=localhost,127.0.0.1,docker-registry.example.com,.corp
   ```

**无根模式（Rootless mode）**

1. 为 `docker` 服务创建一个 systemd 插入目录：

   ```console
   $ mkdir -p ~/.config/systemd/user/docker.service.d
   ```

2. 创建一个名为 `~/.config/systemd/user/docker.service.d/http-proxy.conf` 的文件，添加 `HTTP_PROXY` 环境变量：

   ```systemd
   [Service]
   Environment="HTTP_PROXY=http://proxy.example.com:3128"
   ```

   要代理 HTTPS 请求，设置 `HTTPS_PROXY` 环境变量：

   ```systemd
   [Service]
   Environment="HTTPS_PROXY=http://proxy.example.com:3128"
   ```

   可以设置多个环境变量；同时设置 HTTP 和 HTTPS 代理：

   ```systemd
   [Service]
   Environment="HTTP_PROXY=http://proxy.example.com:3128"
   Environment="HTTPS_PROXY=http://proxy.example.com:3128"
   ```

   > [!NOTE]
   >
   > 代理值中的特殊字符（如 `#?!()[]{}`）必须使用 `%%` 进行双重转义。例如：
   >
   > ```systemd
   > [Service]
   > Environment="HTTP_PROXY=http://domain%%5Cuser:complex%%23pass@proxy.example.com:3128/"
   > ```

3. 如果您需要联系内部 Docker 镜像仓库而不通过代理，可以通过 `NO_PROXY` 环境变量指定它们。

   `NO_PROXY` 变量的说明同常规安装。

   示例：

   ```systemd
   [Service]
   Environment="HTTP_PROXY=http://proxy.example.com:3128"
   Environment="HTTPS_PROXY=http://proxy.example.com:3128"
   Environment="NO_PROXY=localhost,127.0.0.1,docker-registry.example.com,.corp"
   ```

4. 刷新更改并重启 Docker

   ```console
   $ systemctl --user daemon-reload
   $ systemctl --user restart docker
   ```

5. 验证配置已加载并与您所做的更改匹配，例如：

   ```console
   $ systemctl --user show --property=Environment docker

   Environment=HTTP_PROXY=http://proxy.example.com:3128 HTTPS_PROXY=http://proxy.example.com:3128 NO_PROXY=localhost,127.0.0.1,docker-registry.example.com,.corp
   ```