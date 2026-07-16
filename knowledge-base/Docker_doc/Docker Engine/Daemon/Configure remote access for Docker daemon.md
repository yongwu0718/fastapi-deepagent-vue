# 配置 Docker 守护进程的远程访问（Configure remote access for Docker daemon）

默认情况下，Docker 守护进程监听 Unix socket 以接受来自本地客户端的请求。您可以配置 Docker 使其同时监听 IP 地址和端口以及 Unix socket，从而接受来自远程客户端的请求。

> [!WARNING]
>
> 将 Docker 配置为接受来自远程客户端的连接可能会使您的主机容易受到未经授权的访问和其他攻击。
>
> 理解将 Docker 开放到网络的安全隐患至关重要。如果不采取措施保护连接，远程非 root 用户可能获得主机的 root 访问权限。
>
> **不推荐**使用不带 TLS 的远程访问，并且在未来的版本中将需要明确选择加入。有关如何使用 TLS 证书保护此连接的更多信息，请参阅[保护 Docker 守护进程 socket](/engine/security/protect-access/)。

## 启用远程访问（Enable remote access）

您可以为使用 systemd 的 Linux 发行版使用 `docker.service` systemd 单元文件来启用对守护进程的远程访问。如果您的发行版不使用 systemd，则可以使用 `daemon.json` 文件。

同时使用 systemd 单元文件和 `daemon.json` 文件配置 Docker 监听连接会导致冲突，从而阻止 Docker 启动。

### 使用 systemd 单元文件配置远程访问（Configuring remote access with systemd unit file）

1. 使用命令 `sudo systemctl edit docker.service` 在文本编辑器中打开 `docker.service` 的覆盖文件。

2. 添加或修改以下行，替换为您自己的值。

   ```systemd
   [Service]
   ExecStart=
   ExecStart=/usr/bin/dockerd -H fd:// -H tcp://127.0.0.1:2375
   ```

3. 保存文件。

4. 重新加载 `systemctl` 配置。

   ```console
   $ sudo systemctl daemon-reload
   ```

5. 重启 Docker。

   ```console
   $ sudo systemctl restart docker.service
   ```

6. 验证更改是否已生效。

   ```console
   $ sudo netstat -lntp | grep dockerd
   tcp        0      0 127.0.0.1:2375          0.0.0.0:*               LISTEN      3758/dockerd
   ```

### 使用 `daemon.json` 配置远程访问（Configuring remote access with `daemon.json`）

1. 在 `/etc/docker/daemon.json` 中设置 `hosts` 数组，以连接到 Unix socket 和一个 IP 地址，如下所示：

   ```json
   {
     "hosts": ["unix:///var/run/docker.sock", "tcp://127.0.0.1:2375"]
   }
   ```

2. 重启 Docker。

3. 验证更改是否已生效。

   ```console
   $ sudo netstat -lntp | grep dockerd
   tcp        0      0 127.0.0.1:2375          0.0.0.0:*               LISTEN      3758/dockerd
   ```

### 通过防火墙允许访问远程 API（Allow access to the remote API through a firewall）

如果您在与 Docker 相同的主机上运行防火墙，并且希望从另一个远程主机访问 Docker Remote API，则必须配置防火墙以允许在 Docker 端口上的传入连接。如果您使用 TLS 加密传输，默认端口为 `2376`，否则为 `2375`。

两种常见的防火墙守护进程是：

- [Uncomplicated Firewall (ufw)](https://help.ubuntu.com/community/UFW)，常用于 Ubuntu 系统。
- [firewalld](https://firewalld.org)，常用于基于 RPM 的系统。

请查阅您的操作系统和防火墙的文档。以下信息可能对您有所帮助。本说明中使用的设置是宽松的，您可能希望使用不同的配置来进一步锁定您的系统。

- 对于 ufw，在配置中设置 `DEFAULT_FORWARD_POLICY="ACCEPT"`。

- 对于 firewalld，向您的策略添加类似于以下的规则。一条用于传入请求，一条用于传出请求。

  ```xml
  <direct>
    [ <rule ipv="ipv6" table="filter" chain="FORWARD_direct" priority="0"> -i zt0 -j ACCEPT </rule> ]
    [ <rule ipv="ipv6" table="filter" chain="FORWARD_direct" priority="0"> -o zt0 -j ACCEPT </rule> ]
  </direct>
  ```

  确保接口名称和链名称正确。

## 附加信息（Additional information）

有关守护进程远程访问的配置选项的更多详细信息，请参阅 [dockerd CLI 参考](/reference/cli/dockerd/#bind-docker-to-another-hostport-or-a-unix-socket)。