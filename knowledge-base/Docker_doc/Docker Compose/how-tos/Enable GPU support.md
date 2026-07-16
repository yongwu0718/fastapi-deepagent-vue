# 使用 GPU 访问运行 Docker Compose services

如果 Docker 主机包含此类设备并且 Docker Daemon 进行了相应设置，Compose services 可以定义 GPU 设备预留。为此，请确保您已安装[前提条件](/engine/containers/resource_constraints/#gpu)（如果尚未安装）。

以下各节的示例主要侧重于使用 Docker Compose 为 service containers 提供对 GPU 设备的访问。

## 为 service containers 启用 GPU 访问

在需要 GPU 的 service 中，使用 Compose Deploy 规范中的 [device](/reference/compose-file/deploy/#devices) 属性在 `compose.yaml` 文件中引用 GPU。

这提供了对 GPU 预留更细粒度的控制，因为可以为以下 device 属性设置自定义值：

- `capabilities`。该值指定为字符串列表。例如，`capabilities: [gpu]`。您必须在 Compose 文件中设置此字段。否则，在 service 部署时会返回错误。
- `count`。指定为整数或值 `all`，表示应预留的 GPU 设备数量（前提是主机拥有该数量的 GPU）。如果 `count` 设置为 `all` 或未指定，则默认使用主机上所有可用的 GPU。
- `device_ids`。该值指定为字符串列表，表示主机的 GPU 设备 ID。您可以在主机上 `nvidia-smi` 的输出中找到设备 ID。如果未设置 `device_ids`，则默认使用主机上所有可用的 GPU。
- `driver`。指定为字符串，例如 `driver: 'nvidia'`
- `options`。表示驱动特定选项的键值对。

> [!IMPORTANT]
>
> 您必须设置 `capabilities` 字段。否则，在 service 部署时会返回错误。

> [!NOTE]
>
> `count` 和 `device_ids` 是互斥的。您一次只能定义一个字段。

有关这些属性的更多信息，请参阅 [Compose Deploy 规范](/reference/compose-file/deploy/#devices)。

### 用于运行可访问 1 个 GPU 设备的 service 的 Compose 文件示例

```yaml
services:
  test:
    image: nvidia/cuda:12.9.0-base-ubuntu22.04
    command: nvidia-smi
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

使用 Docker Compose 运行：

```console
$ docker compose up
Creating network "gpu_default" with the default driver
Creating gpu_test_1 ... done
Attaching to gpu_test_1    
test_1  | +-----------------------------------------------------------------------------+
test_1  | | NVIDIA-SMI 450.80.02    Driver Version: 450.80.02    CUDA Version: 11.1     |
test_1  | |-------------------------------+----------------------+----------------------+
test_1  | | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
test_1  | | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
test_1  | |                               |                      |               MIG M. |
test_1  | |===============================+======================+======================|
test_1  | |   0  Tesla T4            On   | 00000000:00:1E.0 Off |                    0 |
test_1  | | N/A   23C    P8     9W /  70W |      0MiB / 15109MiB |      0%      Default |
test_1  | |                               |                      |                  N/A |
test_1  | +-------------------------------+----------------------+----------------------+
test_1  |                                                                                
test_1  | +-----------------------------------------------------------------------------+
test_1  | | Processes:                                                                  |
test_1  | |  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
test_1  | |        ID   ID                                                   Usage      |
test_1  | |=============================================================================|
test_1  | |  No running processes found                                                 |
test_1  | +-----------------------------------------------------------------------------+
gpu_test_1 exited with code 0

```

在拥有多个 GPU 的主机上，可以设置 `device_ids` 字段来针对特定的 GPU 设备，并且可以使用 `count` 来限制分配给 service container 的 GPU 设备数量。

您可以在每个 service 定义中使用 `count` 或 `device_ids`。如果您尝试同时使用两者、指定无效的设备 ID，或者使用高于系统中 GPU 数量的 `count` 值，则会返回错误。

```console
$ nvidia-smi   
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 450.80.02    Driver Version: 450.80.02    CUDA Version: 11.0     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                               |                      |               MIG M. |
|===============================+======================+======================|
|   0  Tesla T4            On   | 00000000:00:1B.0 Off |                    0 |
| N/A   72C    P8    12W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
|   1  Tesla T4            On   | 00000000:00:1C.0 Off |                    0 |
| N/A   67C    P8    11W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
|   2  Tesla T4            On   | 00000000:00:1D.0 Off |                    0 |
| N/A   74C    P8    12W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
|   3  Tesla T4            On   | 00000000:00:1E.0 Off |                    0 |
| N/A   62C    P8    11W /  70W |      0MiB / 15109MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
```

## 访问特定设备

仅允许访问 GPU-0 和 GPU-3 设备：

```yaml
services:
  test:
    image: tensorflow/tensorflow:latest-gpu
    command: python -c "import tensorflow as tf;tf.test.gpu_device_name()"
    deploy:
      resources:
        reservations:
          devices:
          - driver: nvidia
            device_ids: ['0', '3']
            capabilities: [gpu]
```