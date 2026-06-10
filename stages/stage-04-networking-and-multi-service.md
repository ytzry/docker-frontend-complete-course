# 第 4 阶段：Docker 网络与多容器协作

![第4阶段配图](../images/docker-stage-4.png)

这一阶段解决三个高频问题：

1. 容器之间为什么能互相访问。
2. 浏览器、前端容器、API 容器、Redis/Postgres 容器分别该访问谁。
3. 为什么 `localhost` 在本机能通，进了容器就失效。

学完这一章，你应该能独立搭起一个前端开发容器、一个 API 容器、一个 Redis 容器和一个 Postgres 容器，并且能准确判断每一跳网络流量走向。

## 学习目标

- 理解 Docker 默认 `bridge` 网络的工作方式
- 理解容器内访问和浏览器访问的目标地址差异
- 掌握通过服务名进行容器间通信
- 掌握前端 + API + Redis/Postgres 的正确连接方式
- 掌握 `Vite proxy` 的适用场景
- 能用常见调试命令定位网络问题

## 先建立正确心智模型

Docker 网络问题本质上是“谁在访问谁”。

- 浏览器访问容器：走宿主机端口映射，例如 `http://localhost:5173`
- 容器访问容器：走 Docker 网络内的服务名，例如 `http://api:3000`
- API 访问数据库或缓存：走 Docker 网络内的服务名，例如 `postgres:5432`、`redis:6379`

这里最容易混淆的是 `localhost`。

- 在宿主机浏览器里，`localhost` 指你的电脑
- 在前端容器里，`localhost` 指前端容器自己
- 在 API 容器里，`localhost` 指 API 容器自己

所以：

- 浏览器里访问 `http://localhost:5173` 很正常
- 前端容器里访问 API 时写 `http://localhost:3000`，通常会失败，因为它会去找前端容器自己的 3000 端口
- API 容器里连接 Redis 时写 `localhost:6379`，通常也会失败，因为 Redis 在另一个容器

## Docker 默认网络：bridge

Docker 默认使用 `bridge` 网络给容器提供隔离环境。你可以把它理解成 Docker 在宿主机里创建的一张虚拟局域网。

特点：

- 同一张自定义 `bridge` 网络中的容器可以互相通信
- 容器之间可以通过服务名或容器名做 DNS 解析
- 宿主机访问容器需要端口映射
- 浏览器无法直接解析 Docker 服务名，例如浏览器不能直接访问 `http://api:3000`

常见命令：

```bash
docker network ls                         # 查看当前 Docker 网络列表
docker network inspect bridge            # 查看默认 bridge 网络详情
docker network create app-net           # 创建自定义 bridge 网络，推荐多容器项目使用
docker network inspect app-net          # 查看自定义网络中的容器、网段和 DNS 信息
```

为什么推荐自定义网络：

- 语义更清晰，项目边界明确
- 容器服务名解析更稳定
- 多项目并行开发时更容易隔离

## 单容器访问和多容器访问的差别

### 场景 1：浏览器访问前端容器

假设你启动了一个运行 Vite 的前端容器：

```bash
# `-it`：进入交互式终端
# `--rm`：退出后自动删除容器
# `-p 5173:5173`：把宿主机 5173 映射到容器 5173
# `-v ${PWD}:/app`：挂载当前项目目录到容器 /app
# `-w /app`：把工作目录切到 /app
docker run -it --rm --name frontend-dev -p 5173:5173 -v ${PWD}:/app -w /app node:20-alpine sh
```

进入容器后启动 Vite：

```bash
npm install                              # 安装当前前端项目依赖
npm run dev -- --host 0.0.0.0           # 让 Vite 监听容器内所有网卡，宿主机才能通过端口映射访问
```

此时浏览器访问：

```text
http://localhost:5173
```

这里的访问路径是：

`浏览器 -> 宿主机 localhost:5173 -> Docker 端口映射 -> 前端容器 5173`

### 场景 2：前端容器访问 API 容器

如果 API 在另一个容器里，前端容器访问 API 应该写：

```text
http://api:3000
```

这里 `api` 是 Docker 网络中的服务名，不是浏览器能识别的公网域名，也不是宿主机上的地址。

访问路径是：

`前端容器 -> Docker DNS 解析 api -> API 容器 3000`

### 场景 3：浏览器访问 API

如果你在浏览器里直接请求 API，则浏览器不能解析 `api`，应该访问宿主机暴露端口，例如：

```text
http://localhost:3000
```

访问路径是：

`浏览器 -> 宿主机 localhost:3000 -> Docker 端口映射 -> API 容器 3000`

这就是为什么同一个 API 服务，在不同位置访问时地址不同。

## 服务名解析：为什么 `api`、`redis`、`postgres` 可以直接访问

在同一个自定义 Docker 网络内，Docker 内置 DNS 会把服务名解析到对应容器 IP。

例子：

- `api` 解析到 API 容器
- `redis` 解析到 Redis 容器
- `postgres` 解析到 Postgres 容器

这也是 Compose 项目里大家更喜欢用服务名通信的原因。容器 IP 会变化，服务名更稳定。

下面先用纯 Docker 命令建立一个最小网络实验。

```bash
docker network create app-net                          # 创建项目网络，给多个容器提供统一通信环境
docker run -d --name redis --network app-net redis:7-alpine        # 启动 Redis 容器，并接入 app-net
docker run -d --name postgres --network app-net -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=appdb postgres:16-alpine   # 启动 Postgres 容器，并设置数据库密码和默认库
docker run -d --name api --network app-net -p 3000:3000 node:20-alpine tail -f /dev/null   # 启动一个 Node 容器并保持常驻，后续用它模拟 API 服务
```

验证服务名解析：

```bash
docker exec -it api sh                                 # 进入 API 容器
ping redis                                             # 测试 API 容器能否解析 redis 服务名
ping postgres                                          # 测试 API 容器能否解析 postgres 服务名
```

有些精简镜像没有 `ping`，你可以换成：

```bash
getent hosts redis                                     # 查看 redis 服务名解析结果
getent hosts postgres                                  # 查看 postgres 服务名解析结果
```

## 前端 + API + Redis + Postgres 的正确通信路径

这一节用前端项目里最常见的四个角色来讲：

- `frontend`: Vite / React / Vue 开发服务器
- `api`: Node.js API 服务
- `redis`: 缓存、会话、队列
- `postgres`: 业务数据库

### 网络拓扑图

```mermaid
flowchart LR
    B["浏览器<br/>localhost:5173"] --> H1["宿主机端口映射"]
    H1 --> F["frontend 容器<br/>Vite Dev Server :5173"]
    F --> P["Vite Proxy<br/>/api -> http://api:3000"]
    P --> A["api 容器<br/>Node API :3000"]
    A --> R["redis 容器<br/>6379"]
    A --> D["postgres 容器<br/>5432"]
```

### 精确解释每一跳

1. 浏览器访问前端页面  
浏览器请求 `http://localhost:5173`，实际进入的是前端容器里的 Vite 开发服务器。

2. 浏览器请求 `/api/users`  
这个请求先发给 Vite 开发服务器。

3. Vite Proxy 转发请求  
Vite 在前端容器内部把 `/api/users` 转发到 `http://api:3000/users`。

4. API 容器处理业务逻辑  
API 容器通过 `redis:6379` 访问缓存，通过 `postgres:5432` 访问数据库。

### 关键结论

- 浏览器里写的地址通常是 `localhost:端口`
- 容器里写的地址通常是 `service-name:端口`
- `Vite proxy` 运行在前端容器里，所以它能访问 `api`

## `localhost`、服务名、浏览器访问的区别

这一段必须彻底吃透。

| 所在位置 | 访问 API 推荐写法 | 原因 |
| --- | --- | --- |
| 宿主机浏览器 | `http://localhost:3000` 或 `/api` | 浏览器认宿主机端口，不认 Docker 服务名 |
| 前端容器里的 Vite proxy | `http://api:3000` | Vite 进程运行在容器内，能通过 Docker DNS 找到 API |
| API 容器访问 Redis | `redis:6379` | Redis 在另一个容器内 |
| API 容器访问 Postgres | `postgres:5432` | Postgres 在另一个容器内 |
| 前端容器访问自己 | `localhost:5173` | `localhost` 指前端容器自身 |
| API 容器访问自己 | `localhost:3000` | `localhost` 指 API 容器自身 |

### 为什么浏览器里不能写 `http://api:3000`

因为浏览器运行在宿主机环境，DNS 解析走的是宿主机网络，不会自动使用 Docker 内部服务名。

### 为什么 Vite proxy 可以写 `http://api:3000`

因为 Vite 进程运行在前端容器里，它已经接入 Docker 网络，Docker DNS 能把 `api` 解析到 API 容器。

## 实战：前端 + API + Redis + Postgres 组合

下面给你一个适合前端工程师理解的 Compose 示例。

```yaml
services:
  frontend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./:/app
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    ports:
      - "5173:5173"
    depends_on:
      - api
    networks:
      - app-net

  api:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./server:/app
    command: sh -c "npm install && node index.js"
    ports:
      - "3000:3000"
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgres://postgres:123456@postgres:5432/appdb
    depends_on:
      - redis
      - postgres
    networks:
      - app-net

  redis:
    image: redis:7-alpine
    networks:
      - app-net

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: 123456
      POSTGRES_DB: appdb
    ports:
      - "5432:5432"
    networks:
      - app-net

networks:
  app-net:
    driver: bridge
```

### 这个结构里谁访问谁

- 浏览器访问前端：`http://localhost:5173`
- 浏览器直连 API：`http://localhost:3000`
- 前端容器里的 Vite proxy 访问 API：`http://api:3000`
- API 访问 Redis：`redis://redis:6379`
- API 访问 Postgres：`postgres://postgres:123456@postgres:5432/appdb`

## Vite Proxy 的正确写法

这是前端开发时最常用的一段配置。

```ts
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://api:3000',
        changeOrigin: true,
      },
    },
  },
})
```

解释：

- `host: '0.0.0.0'`：让 Vite 在容器内对外监听，宿主机可以访问
- `port: 5173`：Vite 在容器内监听 5173
- `target: 'http://api:3000'`：代理目标写 Docker 服务名，因为这个请求由前端容器内部发出

### 开发时推荐访问方式

前端代码里直接请求：

```ts
fetch('/api/users') // 让浏览器先请求 Vite，再由 Vite 代理到 API 容器
```

这样有三个好处：

- 避免前端代码里写死不同环境的 API 域名
- 避免本地开发时跨域处理过重
- 前端和 API 的网络边界更清晰

## 命令示例：从零验证多容器通信

### 1. 创建网络

```bash
docker network create app-net                  # 创建 app-net 网络，后续所有服务都加入这张网络
```

### 2. 启动 Redis

```bash
docker run -d --name redis --network app-net redis:7-alpine   # 启动 Redis，并接入 app-net
```

### 3. 启动 Postgres

```bash
# `--network app-net`：让 Postgres 加入 app-net 网络
# `-e POSTGRES_PASSWORD=123456`：设置数据库超级用户密码
# `-e POSTGRES_DB=appdb`：初始化默认数据库 appdb
docker run -d --name postgres --network app-net -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=appdb postgres:16-alpine   # 启动 Postgres，并初始化密码和数据库
```

### 4. 启动一个 API 测试容器

```bash
docker run -it --rm --name api-test --network app-net node:20-alpine sh   # 启动临时 Node 容器，并加入同一网络
```

进入容器后安装调试工具：

```bash
apk add --no-cache curl bind-tools busybox-extras   # 安装 curl、DNS 工具和网络测试工具
```

测试 Redis 端口：

```bash
nc -zv redis 6379                                   # 检查 redis 服务名对应的 6379 端口是否可连通
```

测试 Postgres 端口：

```bash
nc -zv postgres 5432                                # 检查 postgres 服务名对应的 5432 端口是否可连通
```

查看 DNS 解析：

```bash
nslookup redis                                      # 查询 redis 服务名解析结果
nslookup postgres                                   # 查询 postgres 服务名解析结果
```

## 调试命令

网络问题不要靠猜，直接进容器检查。

```bash
docker ps                                           # 查看当前运行中的容器
docker network ls                                   # 查看 Docker 网络列表
docker network inspect app-net                      # 查看 app-net 里的容器和网络配置
docker exec -it frontend sh                         # 进入前端容器排查问题
docker exec -it api sh                              # 进入 API 容器排查问题
docker logs frontend                                # 查看前端容器日志
docker logs api                                     # 查看 API 容器日志
docker logs postgres                                # 查看 Postgres 容器日志
docker logs redis                                   # 查看 Redis 容器日志
```

进入前端容器后建议执行：

```bash
printenv | grep VITE                                # 查看前端容器中的环境变量
curl http://api:3000/health                         # 在前端容器内测试能否访问 API 健康检查接口
nslookup api                                        # 查看前端容器内是否能解析 api 服务名
```

进入 API 容器后建议执行：

```bash
printenv | grep -E 'REDIS|DATABASE'                 # 查看 API 容器里的 Redis 和数据库连接配置
nc -zv redis 6379                                   # 测试 Redis 端口联通性
nc -zv postgres 5432                                # 测试 Postgres 端口联通性
```

## 常见坑

### 1. 前端容器里把 API 地址写成 `localhost:3000`

症状：

- 浏览器页面能打开
- 接口一直超时或连接拒绝

原因：

- `localhost` 指前端容器自己

正确做法：

- Vite proxy 目标写 `http://api:3000`

### 2. Vite 没有监听 `0.0.0.0`

症状：

- 容器在运行
- 宿主机访问 `localhost:5173` 打不开

原因：

- Vite 只监听了容器内部回环地址

正确做法：

```bash
npm run dev -- --host 0.0.0.0                      # 让 Vite 对容器外部可见
```

### 3. 浏览器直接访问 `http://api:3000`

症状：

- 浏览器提示域名无法解析

原因：

- `api` 是 Docker 内部服务名，浏览器运行在宿主机上

正确做法：

- 浏览器访问 `http://localhost:3000`
- 或浏览器访问 `http://localhost:5173`，再由 Vite proxy 转发到 `api:3000`

### 4. `depends_on` 让你误以为数据库已经可用

症状：

- API 容器已经启动
- 程序一启动就报数据库连接失败

原因：

- `depends_on` 只保证启动顺序，不保证服务已经完成初始化

正确做法：

- 给 API 增加重试逻辑
- 给数据库配置健康检查

### 5. 容器加入了不同网络

症状：

- 服务都在运行
- 服务名互相解析不到

原因：

- `frontend`、`api`、`redis`、`postgres` 没接入同一张网络

正确做法：

- 确保它们都在同一个自定义 `bridge` 网络中

## 练习

### 练习 1：验证服务名解析

要求：

- 创建 `app-net`
- 启动 `redis` 和一个临时 `node:20-alpine` 容器
- 在临时容器中执行 `nslookup redis`

目标：

- 看到 `redis` 能被解析到容器 IP

### 练习 2：搭建前端 + API 双容器通信

要求：

- 前端容器启动 Vite，端口映射 `5173:5173`
- API 容器监听 `3000`
- Vite proxy 把 `/api` 转发到 `http://api:3000`

目标：

- 浏览器访问 `http://localhost:5173`
- 页面里发起 `/api/health` 请求
- API 正常返回数据

### 练习 3：给 API 接入 Redis 和 Postgres

要求：

- API 配置 `REDIS_URL=redis://redis:6379`
- API 配置 `DATABASE_URL=postgres://postgres:123456@postgres:5432/appdb`

目标：

- API 启动时成功连接 Redis 和 Postgres
- 你能在 API 容器里用 `nc -zv` 验证两个端口联通

## 本阶段你应该掌握的结论

- 浏览器访问容器，走宿主机端口映射
- 容器访问容器，走 Docker 网络和服务名解析
- 浏览器里的 `localhost` 和容器里的 `localhost` 含义不同
- `Vite proxy` 运行在前端容器内，所以代理目标应该写服务名
- API 到 Redis/Postgres 的连接地址应该写服务名和容器端口
- 网络问题优先用 `docker exec`、`curl`、`nslookup`、`nc` 逐跳验证

进入下一阶段前，建议你亲手把 `frontend + api + redis + postgres` 这一套在本地跑通一次，并画出自己的请求路径图。
