# 在阿里云上把 ReelMatrix 跑起来（傻瓜版）

整套就是：**放行端口 → 登服务器 → 拉代码 → 填 key → 一键起**。第一次约 10 分钟。

---

## 你需要先准备三样东西

1. **阿里云 ECS**（已开好：杭州 / 2核4G / Ubuntu / 预装 Docker），记下**公网 IP**（例：`121.43.99.199`）。
2. **DashScope（通义千问）API key** —— 去 [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) 开通、创建一个 key（形如 `sk-xxxx`）。
3. **GitHub Personal Access Token** —— 仓库是私有的，拉代码要它。GitHub → Settings → Developer settings → Personal access tokens → 生成一个（勾选 `repo` 权限）。

---

## 第 1 步：放行端口（阿里云控制台里点）

ECS 控制台 → 你的实例 → **安全组** → 配置规则 → **入方向** → 手动添加：
- 端口 **3000**（网站），来源 `0.0.0.0/0`
- 端口 **8000**（后端 API），来源 `0.0.0.0/0`

> 不放行的话，外面打不开网站。

## 第 2 步：登录服务器

Mac 打开「终端」，输入（把 IP 换成你的）：
```bash
ssh root@121.43.99.199
```
输入你在阿里云设的服务器密码。

## 第 3 步：确认 Docker 在（预装了就跳过）

```bash
docker --version || curl -fsSL https://get.docker.com | sh
docker compose version
```

## 第 4 步：拉代码

把 `<TOKEN>` 换成你的 GitHub token（注意 `-b team-os-phase0`，代码在这个分支上）：
```bash
git clone -b team-os-phase0 https://<TOKEN>@github.com/JiimS66/reelmatrix.git
cd reelmatrix
```

## 第 5 步：填配置

```bash
cp .env.deploy.example .env
nano .env
```
在打开的编辑器里：
- `PUBLIC_IP=` 填你的服务器公网 IP（例 `121.43.99.199`）
- `DASHSCOPE_API_KEY=` 填你的通义千问 key

改完按 `Ctrl+O` 回车保存，`Ctrl+X` 退出。

## 第 6 步：一键起

```bash
chmod +x deploy.sh
./deploy.sh
```
等几分钟（第一次要构建镜像）。看到 `✓ Done` 后，浏览器打开：

**http://你的IP:3000**  →  左边点 **Strategy**，就是你试过的策略循环，这次走的是真·通义千问。

---

## 以后怎么更新

- **你本地**：改完代码 → `git push`
- **服务器上**：`cd reelmatrix && ./deploy.sh`（它自动 `git pull` + 重建重启）

## 出问题怎么查

```bash
docker compose logs -f          # 看实时日志，报错都在这
docker compose ps               # 看两个容器是否都 Up
```

- **网站打不开** → 八成是第 1 步端口没放行。
- **能打开但一点策略就报错** → `.env` 里 `DASHSCOPE_API_KEY` 没填对，或 DashScope 没开通/没额度。
- **想省钱** → 不用时去阿里云控制台把实例 **停机**（停了不算免费时长）。

## 想换成本地开源模型（以后验证 on-prem 卖点时）

把 `.env` 改成 `LLM_PROVIDER=local` + 指向你的 Ollama/vLLM 地址即可，业务代码一行不用动——这正是 provider 工厂的意义。
