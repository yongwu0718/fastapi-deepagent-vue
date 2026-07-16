# 使用 IPv6 网络（Use IPv6 networking）

IPv6 仅在运行于 Linux 主机的 Docker 守护进程上受支持。

## 创建 IPv6 网络（Create an IPv6 network）

- 使用 `docker network create`：

  ```console
  $ docker network create --ipv6 ip6net
  ```

- 使用 `docker network create` 并指定 IPv6 子网：

  ```console
  $ docker network create --ipv6 --subnet 2001:db8::/64 ip6net
  ```

- 使用 Docker Compose 文件：

  ```yaml
   networks:
     ip6net:
       enable_ipv6: true
       ipam:
         config:
           - subnet: 2001:db8::/64
  ```

> [!NOTE]
>
> 这些示例中的地址 `2001:db8::/64` 是[文档中保留使用的][wikipedia-ipv6-reserved]。
> 请将其替换为有效的 IPv6 网络，例如来自 `fd00::/8` 的[唯一本地地址（ULA）][wikipedia-ipv6-ula]子网。

现在你可以运行附加到 `ip6net` 网络的容器了。

```console
$ docker run --rm --network ip6net -p 80:80 traefik/whoami
```

这将在 IPv6 和 IPv4 上同时发布端口 80。你可以通过运行 curl 来验证 IPv6 连接，连接到 IPv6 回环地址的 80 端口：

```console
$ curl http://[::1]:80
Hostname: ea1cfde18196
IP: 127.0.0.1
IP: ::1
IP: 172.17.0.2
IP: 2001:db8::2
IP: fe80::42:acff:fe11:2
RemoteAddr: [2001:db8::1]:37574
GET / HTTP/1.1
Host: [::1]
User-Agent: curl/8.1.2
Accept: */*
```

## 为默认 **bridge** 网络使用 IPv6

以下步骤向你展示如何在默认 **bridge** 网络上使用 IPv6。

1. 编辑 Docker **daemon** 配置文件，位于 `/etc/docker/daemon.json`。配置以下参数：

   ```json
   {
     "ipv6": true,
     "fixed-cidr-v6": "2001:db8:1::/64"
   }
   ```

   > [!NOTE]
   >
   > 此示例中的地址 `2001:db8:1::/64` 是[文档中保留使用的][wikipedia-ipv6-reserved]。
   > 请将其替换为有效的 IPv6 网络，例如来自 `fd00::/8` 的[唯一本地地址（ULA）][wikipedia-ipv6-ula]子网。

   - `ipv6` 在默认网络上启用 IPv6 网络。
   - `fixed-cidr-v6` 为默认 **bridge** 网络分配一个子网，启用动态 IPv6 地址分配。
   - `ip6tables` 启用额外的 IPv6 包过滤规则，提供网络隔离和端口映射。它默认启用，但可以禁用。

2. 保存配置文件。
3. 重启 Docker **daemon** 使更改生效。

   ```console
   $ sudo systemctl restart docker
   ```

现在你可以在默认 **bridge** 网络上运行容器了。

```console
$ docker run --rm -p 80:80 traefik/whoami
```

这将在 IPv6 和 IPv4 上同时发布端口 80。你可以通过对 IPv6 回环地址的 80 端口发起请求来验证 IPv6 连接：

```console
$ curl http://[::1]:80
Hostname: ea1cfde18196
IP: 127.0.0.1
IP: ::1
IP: 172.17.0.2
IP: 2001:db8:1::242:ac12:2
IP: fe80::42:acff:fe12:2
RemoteAddr: [2001:db8:1::1]:35558
GET / HTTP/1.1
Host: [::1]
User-Agent: curl/8.1.2
Accept: */*
```

## 动态 IPv6 子网分配（Dynamic IPv6 subnet allocation）

如果你没有为用户定义的网络显式配置子网（即使用 `docker network create --subnet=<your-subnet>`），那么这些网络将回退使用 **daemon** 的默认地址池（default address pools）。这也适用于从 Docker Compose 文件创建且 `enable_ipv6` 设置为 `true` 的网络。

如果 Docker Engine 的 `default-address-pools` 中没有包含 IPv6 池，并且没有提供 `--subnet` 选项，则在启用 IPv6 时将使用[唯一本地地址（ULA）][wikipedia-ipv6-ula]。这些 `/64` 子网包含一个基于 Docker Engine 随机生成 ID 的 40 位全局 ID，以保证很高的唯一性概率。

内置的默认地址池配置在[子网分配（Subnet allocation）](/engine/network/#subnet-allocation)中有说明。它不包含任何 IPv6 池。

要使用不同的 IPv6 子网池进行动态地址分配，你必须手动配置 **daemon** 的地址池以包含：

- 默认的 IPv4 地址池
- 一个或多个你自己的 IPv6 池

以下示例展示了一个包含 IPv4 和 IPv6 池的有效配置，两个池都提供 256 个子网。前缀长度为 `/24` 的 IPv4 子网将从 `/16` 的池中分配。前缀长度为 `/64` 的 IPv6 子网将从 `/56` 的池中分配。

```json
{
  "default-address-pools": [
    { "base": "172.17.0.0/16", "size": 24 },
    { "base": "2001:db8::/56", "size": 64 }
  ]
}
```

> [!NOTE]
>
> 此示例中的地址 `2001:db8::` 是[文档中保留使用的][wikipedia-ipv6-reserved]。
> 请将其替换为有效的 IPv6 网络。
>
> 默认的 IPv4 池来自私有地址范围，类似于默认的 IPv6 [ULA][wikipedia-ipv6-ula] 网络。

有关 `default-address-pools` 的更多信息，请参阅[子网分配（Subnet allocation）](/engine/network/#subnet-allocation)。

[wikipedia-ipv6-reserved]: https://en.wikipedia.org/wiki/Reserved_IP_addresses#IPv6
[wikipedia-ipv6-ula]: https://en.wikipedia.org/wiki/Unique_local_address

## 嵌套 Docker（Docker in Docker）

在使用 `xtables`（传统的 `iptables`）而不是 `nftables` 的主机上，必须加载内核模块 `ip6_tables` 才能创建 IPv6 Docker 网络。通常，该模块会在 Docker 启动时自动加载。

但是，如果你运行的 Docker in Docker 不是基于最新版本的[官方 `docker` 镜像](https://hub.docker.com/_/docker)，你可能需要在主机上运行 `modprobe ip6_tables`。或者，使用 **daemon** 选项 `--ip6tables=false` 来禁用容器化 Docker Engine 的 `ip6tables`。

## 下一步（Next steps）

- [网络概述（Networking overview）](/engine/network/)
