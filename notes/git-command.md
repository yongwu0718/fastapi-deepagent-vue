## 🔄 本地修改同步到 GitHub 流程（个人项目）

适用场景：已有本地仓库并关联了远程，需要将代码变更推送到 `master` / `main` 分支。

**1. 查看工作区变更**

```bash
git status
```

确认哪些文件被修改、新增或删除。

**2. 暂存所有变更**

```bash
git add .
```

**3. 提交到本地仓库**

```bash
git commit -m "描述本次修改"
```

```bash
git commit --amend --no-edit
```

**4. 拉取远程最新代码（避免冲突）**

```bash
git pull --rebase origin master
```

**5. 推送到 GitHub**

```bash
git push origin master
```

```bash
git push -u origin master:main
```

> 💡 **快捷版（无冲突时）**
>
> ```bash
> git add .
> git commit -m "update"
> git pull --rebase origin main
> git push
> ```

***

### 🔁 完整循环示例（从零开始克隆并推送修改）

**1. 克隆远程仓库**

```bash
git clone git@github.com:yongwu0718/index-rag.git
cd index-rag
```

**2. 修改文件后，重复上述同步流程**

```bash
git add .
git commit -m "feat: add new feature"
git pull --rebase origin master
git push
```

这样就能把本地修改安全地同步到 GitHub 了。

## 🔄 移除本地文件夹（保留 Git 仓库中的记录）

*适用场景：比如* *`node_modules`、`dist`、`.idea`* *或包含敏感信息的配置文件夹，你本地还要用，但不想让它出现在 GitHub/GitLab 上。*

1. **停止追踪该文件夹**（关键参数是 `-r` 和 `--cached`）：

```bash
git rm -r --cached <文件夹名称>
```

*(注：`-r`* *表示递归处理文件夹内的所有内容，`--cached`* *表示只删除 Git 记录，**绝不删除**你电脑上的本地文件)*

1. **提交更改**：

```bash
git commit -m "chore: 停止追踪文件夹 <文件夹名称>"
```

1. **推送到远程仓库**：

```bash
git push
```

1. **⚠️ 必须做的一步**：打开项目根目录的 `.gitignore` 文件，把这个文件夹的名字加进去，防止下次 `git add .` 时又把它加回去。

```text
# .gitignore 文件中添加
<文件夹名称>/
```

## Git 高频命令清单

已统一使用 `bash` 代码块格式，可直接复制使用。注释内为实际工作场景的最佳实践说明。

获取远程最新数据，不自动合并（安全探查）

```bash
git fetch origin
```

拉取远程 main 并自动 merge 合并

```bash
git pull origin main
```

拉取并变基（推荐：保持提交历史线性，避免多余 merge 节点）

```bash
git pull --rebase origin main
```

仅允许快进合并，有冲突则中断（适合 CI/CD 或严格规范团队）

```bash
git pull --ff-only
```

推送当前分支到远程 main

```bash
git push origin main
```

首次推送并建立本地与远程的追踪关联

```bash
git push -u origin feature/login
```

安全强制推送（推送前检查远程是否被他人更新，防覆盖）

```bash
git push --force-with-lease
```

将本地所有标签同步到远程仓库

```bash
git push origin --tags
```

删除远程分支（慎用）

```bash
git push --delete origin branch
```

**📤 推送 (Push)**（标题保留）\
*（以下均为推送相关命令，已提取注释）*

简短格式查看工作区状态（M=修改, ??=未跟踪, A=已暂存）

```bash
git status -s
```

将所有变更加入暂存区

```bash
git add .
```

交互式逐块暂存（精准控制提交内容）

```bash
git add -p
```

规范提交（推荐遵循 Conventional Commits）

```bash
git commit -m "feat: 添加用户登录"
```

修改最后一次提交（可补充漏提交的文件或修正 commit message）

```bash
git commit --amend
```

**📝 日常开发核心 (Daily Workflow)**

创建并切换到新分支（替代 checkout -b）

```bash
git switch -c feature/xxx
```

切换分支

```bash
git switch main
```

查看本地与所有远程分支

```bash
git branch -a
```

安全删除已合并的本地分支

```bash
git branch -d feature/xxx
```

强制删除未合并分支（⚠️ 数据丢失风险）

```bash
git branch -D feature/xxx
```

**🌿 分支管理 (Branching)**

合并指定分支到当前分支

```bash
git merge feature/xxx
```

强制生成 merge 节点，保留功能分支完整历史

```bash
git merge --no-ff feature/xxx
```

将当前分支变基到 main（同步主干最新代码）

```bash
git rebase main
```

交互式压缩/修改/重排最近 3 次提交

```bash
git rebase -i HEAD~3
```

单独摘取某个提交应用到当前分支

```bash
git cherry-pick <commit-hash>
```

**🔄 合并与历史整理 (Merge & Rebase)**

丢弃工作区对文件的修改（不丢暂存）

```bash
git restore file.txt
```

将文件移出暂存区（内容保留，回到未 add 状态）

```bash
git restore --staged file.txt
```

撤销最后一次提交，变更保留在暂存区

```bash
git reset --soft HEAD~1
```

退到上一次提交（⚠️ 工作区与暂存区全清）

```bash
git reset --hard HEAD~1
```

生成一次反向提交（安全撤销，推荐团队协作使用）

```bash
git revert HEAD
```

**↩️ 撤销与恢复 (Undo)**

暂存当前未提交修改，可附加说明

```bash
git stash push -m "临时切分支改Bug"
```

查看暂存列表

```bash
git stash list
```

恢复最新暂存并删除记录

```bash
git stash pop
```

恢复指定暂存（保留记录，可多次应用）

```bash
git stash apply stash@{0}
```

图形化查看最近 10 条提交历史

```bash
git log --oneline --graph --all -10
```

**📦 临时保存现场 (Stash)**

按时间/作者过滤提交

```bash
git log --since="2024-10-01" --author="zhangsan"
```

按作者过滤提交（短格式）

```bash
git log --oneline --author="zhangsan"
```

查看工作区与暂存区的差异

```bash
git diff
```

查看工作区的差异（与 HEAD 比较）

```bash
git diff HEAD
```

查看暂存区与最新提交的差异

```bash
git diff --staged
```

查看指定行最后修改人与提交记录

```bash
git blame -L 10,20 src/app.js
```

**🔍 日志与对比 (Log & Diff)**
