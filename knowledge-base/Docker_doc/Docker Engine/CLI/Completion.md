# 命令补全（Completion）

你可以使用 `docker completion` 命令为 Docker CLI 生成 shell 补全脚本。当你在终端中输入命令并按 `<Tab>` 键时，补全脚本可以为你补全命令、标志以及 Docker 对象（如容器和卷的名称）。

你可以为以下 shell 生成补全脚本：

- [Bash](#bash)
- [Zsh](#zsh)
- [fish](#fish)

## Bash

要为 Bash 获取 Docker CLI 补全功能，你首先需要安装 `bash-completion` 包，该包包含许多用于 shell 补全的 Bash 函数。

```bash
# 使用 APT 安装：
sudo apt install bash-completion

# 使用 Homebrew 安装（Bash 4 或更高版本）：
brew install bash-completion@2
# 为旧版 Bash 安装 Homebrew：
brew install bash-completion

# 使用 pacman 安装：
sudo pacman -S bash-completion
```

安装 `bash-completion` 后，在你的 shell 配置文件（本例中为 `.bashrc`）中加载该脚本：

```bash
# 在 Linux 上：
cat <<EOT >> ~/.bashrc
if [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
fi
EOT

# 在 macOS / 使用 Homebrew 时：
cat <<EOT >> ~/.bash_profile
[[ -r "$(brew --prefix)/etc/profile.d/bash_completion.sh" ]] && . "$(brew --prefix)/etc/profile.d/bash_completion.sh"
EOT
```

然后重新加载你的 shell 配置：

```console
$ source ~/.bashrc
```

现在你可以使用 `docker completion` 命令生成 Bash 补全脚本：

```console
$ mkdir -p ~/.local/share/bash-completion/completions
$ docker completion bash > ~/.local/share/bash-completion/completions/docker
```

## Zsh

Zsh 的[补全系统](http://zsh.sourceforge.net/Doc/Release/Completion-System.html)会负责处理，只要补全脚本可以通过 `FPATH` 被加载。

如果你使用 **Oh My Zsh**，可以通过将补全脚本存储在 `~/.oh-my-zsh/completions` 目录中来安装补全，而无需修改 `~/.zshrc`。

```console
$ mkdir -p ~/.oh-my-zsh/completions
$ docker completion zsh > ~/.oh-my-zsh/completions/_docker
```

如果你不使用 **Oh My Zsh**，可以将补全脚本存储在你选择的目录中，并在你的 `.zshrc` 中将该目录添加到 `FPATH`。

```console
$ mkdir -p ~/.docker/completions
$ docker completion zsh > ~/.docker/completions/_docker
```

```console
$ cat <<"EOT" >> ~/.zshrc
FPATH="$HOME/.docker/completions:$FPATH"
autoload -Uz compinit
compinit
EOT
```

## fish

fish shell 原生支持[补全系统](https://fishshell.com/docs/current/#tab-completion)。要为 Docker 命令激活补全，请将补全脚本复制或符号链接到你的 fish shell 的 `completions/` 目录：

```console
$ mkdir -p ~/.config/fish/completions
$ docker completion fish > ~/.config/fish/completions/docker.fish
```