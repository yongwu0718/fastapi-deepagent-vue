```json
{
  "$schema": "https://langgra.ph/schema.json",
  #"." 表示当前目录,"toml" 表示 在主目录下的 pyproject.toml 文件中加载依赖。".." 表示 上一级目录。
  "dependencies": ["."],
  # graph 编译完成的路径。"agent"是graph的 graph id。
  "graphs": {
    "agent": "backend/agent/instance.py:index_agent"
  },
  # 环境变量可以是本地文件、远程文件或内联设置。
  "env": ".env",
  # 配置 checkpoint 的 TTL。
  "checkpointer": {
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 60,
      "default_ttl": 43200
    },
  },
  # 配置 store 的 TTL。
  "store": {
    "path": "./src/agent/store.py:generate_store",
    "ttl": {
      "refresh_on_read": true,
      "sweep_interval_minutes": 120,
      "default_ttl": 10080
    }
  },
  "python_version": "3.12",
  # 部署应用的镜像分布。
  "image_distro": "wolfi"
}
```