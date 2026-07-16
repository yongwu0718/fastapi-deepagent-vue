# Docker Desktop for Windows 中的 **GPU** 支持

> [!NOTE]
>
> Docker Desktop 中的 **GPU** 支持仅在具有 WSL2 后端的 Windows 上可用。

Docker Desktop for Windows 支持 NVIDIA GPU 上的 **NVIDIA GPU 准虚拟化 (GPU-PV)**，允许容器访问 **GPU** 资源以处理计算密集型工作负载，例如 AI、机器学习或视频处理。

## 先决条件 (Prerequisites)

要启用 WSL 2 **GPU** 准虚拟化，您需要：

- 一台具有 NVIDIA **GPU** 的 Windows 机器
- 更新到最新版本的 Windows 10 或 Windows 11 安装
- NVIDIA 提供的支持 WSL 2 **GPU** 准虚拟化的[最新驱动程序](https://developer.nvidia.com/cuda/wsl)
- 最新版本的 WSL 2 Linux 内核。在命令行中使用 `wsl --update`
- 确保在 Docker Desktop 中[打开 WSL 2 后端](/desktop/features/gpu/wsl/#turn-on-docker-desktop-wsl-2)

## 验证 **GPU** 支持 (Validate GPU support)

要确认容器内 **GPU** 访问正常工作，请运行以下命令：

```console
$ docker run --rm -it --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark
```

这将在 **GPU** 上运行一个 n-body 模拟基准测试。输出类似于：

```console
Run "nbody -benchmark [-numbodies=<numBodies>]" to measure performance.
        -fullscreen       (run n-body simulation in fullscreen mode)
        -fp64             (use double precision floating point values for simulation)
        -hostmem          (stores simulation data in host memory)
        -benchmark        (run benchmark to measure performance)
        -numbodies=<N>    (number of bodies (>= 1) to run in simulation)
        -device=<d>       (where d=0,1,2.... for the CUDA device to use)
        -numdevices=<i>   (where i=(number of CUDA devices > 0) to use for simulation)
        -compare          (compares simulation results running once on the default GPU and once on the CPU)
        -cpu              (run n-body simulation on the CPU)
        -tipsy=<file.bin> (load a tipsy model file for simulation)

> NOTE: The CUDA Samples are not meant for performance measurements. Results may vary when GPU Boost is enabled.

> Windowed mode
> Simulation data stored in video memory
> Single precision floating point simulation
> 1 Devices used for simulation
MapSMtoCores for SM 7.5 is undefined.  Default to use 64 Cores/SM
GPU Device 0: "GeForce RTX 2060 with Max-Q Design" with compute capability 7.5

> Compute 7.5 CUDA device: [GeForce RTX 2060 with Max-Q Design]
30720 bodies, total time for 10 iterations: 69.280 ms
= 136.219 billion interactions per second
= 2724.379 single-precision GFLOP/s at 20 flops per interaction
```

## 运行真实世界模型：使用 Docker Model Runner 运行 **SmolLM2**

使用 Docker Model Runner 通过 vLLM 和 **GPU** 加速来运行 SmolLM2 LLM：

```console
$ docker model install-runner --backend vllm --gpu cuda
```

检查是否正确安装：

```console
$ docker model status
Docker Model Runner is running

Status:
llama.cpp: running llama.cpp version: c22473b
vllm: running vllm version: 0.11.0
```

运行模型：

```console
$ docker model run ai/smollm2-vllm hi
Hello! I'm sure everything goes smoothly here. How can I assist you today?
```