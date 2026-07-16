# None 网络驱动（None network driver）

如果您想完全隔离容器的网络栈，可以在启动容器时使用 `--network none` 标志。在容器内部，只会创建环回设备（loopback device）。

以下示例展示了在使用 `none` 网络驱动的 `alpine` 容器中执行 `ip link show` 的输出。

```console
$ docker run --rm --network none alpine:latest ip link show
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
```

使用 `none` 驱动的容器不会配置 IPv6 环回地址。

```console
$ docker run --rm --network none --name no-net-alpine alpine:latest ip addr show
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
```

## 下一步（Next steps）

- 了解[从容器角度的网络（networking from the container's point of view）](/engine/drivers/)
- 了解 [host 网络（host networking）](/engine/network/drivers/none/host/)
- 了解 [bridge 网络（bridge networks）](/engine/network/drivers/none/bridge/)
- 了解 [overlay 网络（overlay networks）](/engine/network/drivers/none/overlay/)
- 了解 [Macvlan 网络（Macvlan networks）](/engine/network/drivers/none/macvlan/)