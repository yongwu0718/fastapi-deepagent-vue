# 将 **USB/IP** 与 Docker Desktop 结合使用

**USB/IP** 使您能够通过网络共享 USB 设备，然后可以从 Docker 容器内部访问这些设备。本页主要介绍共享连接到运行 Docker Desktop 所在机器的 USB 设备。您可以根据需要重复以下过程来附加和使用其他 USB 设备。

> [!NOTE]
>
> Docker Desktop 包含许多常见 USB 设备的内置驱动程序，但 Docker 无法保证所有 USB 设备都能在此设置下正常工作。

## 设置与使用

### 第一步：运行 **USB/IP** 服务器

要使用 **USB/IP**，您需要运行一个 **USB/IP** 服务器。本指南将使用 [jiegec/usbip](https://github.com/jiegec/usbip) 提供的实现。

1. 克隆仓库。

    ```console
    $ git clone https://github.com/jiegec/usbip
    $ cd usbip
    ```

2. 运行模拟的**人机接口设备 (HID)** 示例。

    ```console
    $ env RUST_LOG=info cargo run --example hid_keyboard
    ```

### 第二步：启动一个特权 Docker 容器

要附加 USB 设备，请启动一个 **PID 命名空间**设置为 `host` 的特权 Docker 容器：

```console
$ docker run --rm -it --privileged --pid=host alpine
```

`--privileged` 授予容器对主机的完全访问权限，`--pid=host` 允许容器共享主机的进程命名空间。

### 第三步：进入 PID 1 的挂载命名空间

在容器内部，进入 `init` 进程的挂载命名空间，以获得对预安装的 **USB/IP 工具**的访问权限：

```console
$ nsenter -t 1 -m
```

### 第四步：使用 **USB/IP 工具**

现在您可以像在其他系统上一样使用 **USB/IP 工具**：

#### 列出 USB 设备

要从主机列出可导出的 USB 设备：

```console
$ usbip list -r host.docker.internal
```

预期输出：

```console
Exportable USB devices
======================
 - host.docker.internal
      0-0-0: unknown vendor : unknown product (0000:0000)
           : /sys/bus/0/0/0
           : (Defined at Interface level) (00/00/00)
           :  0 - unknown class / unknown subclass / unknown protocol (03/00/00)
```

#### 附加一个 USB 设备

要附加特定的 USB 设备（在本例中为模拟键盘）：

```console
$ usbip attach -r host.docker.internal -d 0-0-0
```

#### 验证设备附加

附加模拟键盘后，检查 `/dev/input` 目录中的设备节点：

```console
$ ls /dev/input/
```

示例输出：

```console
event0  mice
```

### 第五步：从另一个容器访问设备

保持初始容器运行以维持 USB 设备的可用性，同时您可以从另一个容器访问已附加的设备。例如：

1. 启动一个新容器，并挂载该设备。

    ```console
    $ docker run --rm -it --device "/dev/input/event0" alpine
    ```

2. 安装一个像 `evtest` 这样的工具来测试模拟键盘。

    ```console
    $ apk add evtest
    $ evtest /dev/input/event0
    ```

3. 与设备交互，观察输出。

    示例输出：

    ```console
    Input driver version is 1.0.1
    Input device ID: bus 0x3 vendor 0x0 product 0x0 version 0x111
    ...
    Properties:
    Testing ... (interrupt to exit)
    Event: time 1717575532.881540, type 4 (EV_MSC), code 4 (MSC_SCAN), value 7001e
    Event: time 1717575532.881540, type 1 (EV_KEY), code 2 (KEY_1), value 1
    Event: time 1717575532.881540, -------------- SYN_REPORT ------------
    ...
    ```

> [!IMPORTANT]
>
> 初始容器必须保持运行状态，以维持与 USB 设备的连接。退出容器将导致设备停止工作。
