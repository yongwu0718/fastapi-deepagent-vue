# 替代容器运行时（Alternative container runtimes）

Docker Engine 使用 **containerd** 来管理容器的生命周期，包括创建、启动和停止容器。默认情况下，**containerd** 使用 **runc** 作为其容器运行时。

## 我可以使用哪些运行时？

您可以使用任何实现了 **containerd** [shim API](https://github.com/containerd/containerd/blob/main/core/runtime/v2/README.md) 的运行时。这类运行时自带 **containerd** shim，无需额外配置即可使用。请参阅[使用 containerd shims](#use-containerd-shims)。

实现了自有 **containerd** shim 的运行时示例包括：

- [Wasmtime](https://wasmtime.dev/)
- [gVisor](https://github.com/google/gvisor)
- [Kata Containers](https://katacontainers.io/)

您也可以使用设计为 **runc** 直接替代品的运行时。这类运行时依赖于 **runc** **containerd** shim 来调用运行时二进制文件。您必须在守护进程配置中手动注册此类运行时。

[youki](https://github.com/youki-dev/youki) 是一个可以作为 **runc** 直接替代品运行的运行时示例。请参考[youki 示例](#youki)了解设置方法。

## 使用 containerd shims

**containerd** shim 允许您使用替代运行时，而无需更改 Docker 守护进程的配置。要使用 **containerd** shim，请将 shim 二进制文件安装在运行 Docker 守护进程的系统上的 `PATH` 中。

要在 `docker run` 中使用 shim，请将运行时的完全限定名称作为 `--runtime` 标志的值：

```console
$ docker run --runtime io.containerd.kata.v2 hello-world
```

### 不安装到 PATH 而使用 containerd shim

您可以在不安装到 `PATH` 的情况下使用 shim，这种情况下需要在守护进程配置中按如下方式注册 shim：

```json
{
  "runtimes": {
    "foo": {
      "runtimeType": "/path/to/containerd-shim-foobar-v1"
    }
  }
}
```

要使用该 shim，请指定您为其分配的名称：

```console
$ docker run --runtime foo hello-world
```

### 配置 shim

如果需要为 **containerd** shim 传递额外配置，可以使用守护进程配置文件中的 `runtimes` 选项。

1. 编辑守护进程配置文件，为您要配置的 shim 添加 `runtimes` 条目。

   - 在 `runtimeType` 键中指定运行时的完全限定名称
   - 在 `options` 键下添加您的运行时配置

   ```json
   {
     "runtimes": {
       "gvisor": {
         "runtimeType": "io.containerd.runsc.v1",
         "options": {
           "TypeUrl": "io.containerd.runsc.v1.options",
           "ConfigPath": "/etc/containerd/runsc.toml"
         }
       }
     }
   }
   ```

2. 重新加载守护进程配置。

   ```console
   # systemctl reload docker
   ```

3. 在 `docker run` 中使用 `--runtime` 标志来使用自定义运行时。

   ```console
   $ docker run --runtime gvisor hello-world
   ```

有关 **containerd** shim 配置选项的更多信息，请参阅[配置 containerd shim](/reference/cli/dockerd/#configure-containerd-shims)。

## 示例

以下示例向您展示如何在 Docker Engine 中设置和使用替代容器运行时。

- [youki](#youki)
- [Wasmtime](#wasmtime)

### youki

**youki** 是一个用 Rust 编写的容器运行时。**youki** 声称比 **runc** 更快、内存占用更少，因此它是资源受限环境下的不错选择。

**youki** 可以作为 **runc** 的直接替代品，这意味着它依赖 **runc** shim 来调用运行时二进制文件。当您注册作为 **runc** 替代品的运行时，您需要配置运行时可执行文件的路径，以及可选的一组运行时参数。更多信息请参阅[配置 runc 直接替代品](/reference/cli/dockerd/#configure-runc-drop-in-replacements)。

要将 **youki** 添加为容器运行时：

1. 安装 **youki** 及其依赖项。

   有关说明，请参考[官方设置指南](https://youki-dev.github.io/youki/user/basic_setup.html)。

2. 通过编辑 Docker 守护进程配置文件（默认位于 `/etc/docker/daemon.json`）来将 **youki** 注册为 Docker 的运行时。

   `path` 键应指定您安装 **youki** 的路径。

   ```console
   # cat > /etc/docker/daemon.json <<EOF
   {
     "runtimes": {
       "youki": {
         "path": "/usr/local/bin/youki"
       }
     }
   }
   EOF
   ```

3. 重新加载守护进程配置。

   ```console
   # systemctl reload docker
   ```

现在您可以运行使用 **youki** 作为运行时的容器。

```console
$ docker run --rm --runtime youki hello-world
```

### Wasmtime

**Wasmtime** 是一个 [Bytecode Alliance](https://bytecodealliance.org/) 项目，也是一个 Wasm 运行时，允许您运行 Wasm 容器。使用 Docker 运行 Wasm 容器提供了双重安全层：您既能获得容器隔离的所有好处，又能获得 Wasm 运行时环境提供的额外沙箱。

要将 **Wasmtime** 添加为容器运行时，请遵循以下步骤：

1. 在守护进程配置文件中启用 [**containerd image store**](/engine/storage/containerd/) 功能。

   ```json
   {
     "features": {
       "containerd-snapshotter": true
     }
   }
   ```

2. 重启 Docker 守护进程。

   ```console
   # systemctl restart docker
   ```

3. 将 **Wasmtime** **containerd** shim 安装到 `PATH` 中。

   以下 Dockerfile 命令从源码构建 **Wasmtime** 二进制文件并将其导出到 `./containerd-shim-wasmtime-v1`。

   ```console
   $ docker build --output . - <<EOF
   FROM rust:latest as build
   RUN cargo install \
       --git https://github.com/containerd/runwasi.git \
       --bin containerd-shim-wasmtime-v1 \
       --root /out \
       containerd-shim-wasmtime
   FROM scratch
   COPY --from=build /out/bin /
   EOF
   ```

   将二进制文件放到 `PATH` 中的某个目录下。

   ```console
   $ mv ./containerd-shim-wasmtime-v1 /usr/local/bin
   ```

现在您可以运行使用 **Wasmtime** 作为运行时的容器。

```console
$ docker run --rm \
 --runtime io.containerd.wasmtime.v1 \
 --platform wasi/wasm32 \
 michaelirwin244/wasm-example
```

## 相关信息

- 要了解有关容器运行时配置选项的更多信息，请参阅[配置容器运行时](/reference/cli/dockerd/#configure-container-runtimes)。
- 您可以配置守护进程应使用的默认运行时。请参阅[配置默认容器运行时](/reference/cli/dockerd/#configure-the-default-container-runtime)。