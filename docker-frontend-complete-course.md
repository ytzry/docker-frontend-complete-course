# 面向前端开发者的 Docker 完整教程

适用读者：HTML/CSS/JavaScript、Node.js、Vite、React、Vue 前端开发者。

学习目标：用 Docker 统一前端开发环境，构建生产镜像，管理多容器开发环境，并衔接 CI/CD、安全与 Kubernetes。

## 课程总览

| 阶段 | 主题 | 你会掌握 |
|---|---|---|
| 第 1 阶段 | 容器基础与 Docker 入门 | 镜像、容器、Dockerfile、Vite 项目容器化 |
| 第 2 阶段 | 镜像与容器操作 | 镜像管理、容器生命周期、端口映射、目录挂载 |
| 第 3 阶段 | Dockerfile 与自定义镜像 | 多阶段构建、缓存、`.dockerignore`、Nginx 托管 SPA |
| 第 4 阶段 | Docker 网络与多容器协作 | bridge 网络、服务名通信、前端 + API + Redis/Postgres |
| 第 5 阶段 | Docker Compose | 用一个 YAML 启动前端、API、数据库、缓存 |
| 第 6 阶段 | 实战与最佳实践 | 镜像优化、非 root、Secret、日志排错、CI/CD |
| 第 7 阶段 | 安全基础与 Kubernetes 衔接 | 镜像扫描、最小权限、Compose 到 K8s 的映射 |

---

## 第 1 阶段：容器基础与 Docker 入门

![第1阶段配图](images/docker-stage-1.png)

### 学习目标

掌握 Docker 的基础工作流：把前端项目源码打包成镜像，启动为容器，并通过浏览器访问运行中的应用。

```mermaid
flowchart LR
  A["源码<br/>HTML/CSS/JS<br/>Vite/React/Vue"] --> B["Dockerfile<br/>定义构建步骤"]
  B --> C["镜像<br/>可复用运行包"]
  C --> D["容器<br/>运行中的应用实例"]
  D --> E["浏览器访问<br/>http://localhost:端口"]
```

### 核心概念

**Docker**

Docker 是打包、分发、运行应用的容器平台。它把应用代码、运行环境、依赖、启动命令放进统一环境，降低团队环境差异带来的问题。

**镜像 Image**

镜像是应用的只读运行包，包含 Node.js、依赖、构建产物、启动命令等。前端视角里，镜像是一份固定版本的项目运行快照。

**容器 Container**

容器是镜像启动后的运行实例。一个镜像可以启动多个容器，就像同一个前端模板可以开多个开发环境。

**仓库 Registry**

仓库用于存放镜像，例如 Docker Hub、GitHub Container Registry、公司私有镜像仓库。它类似 npm registry，用来发布和拉取版本化产物。

**Dockerfile**

Dockerfile 是镜像的构建说明书，写明基础环境、复制文件、安装依赖、构建项目、暴露端口、启动命令。

### 前端视角类比

- `Dockerfile` 类似 `package.json + 构建脚本 + 环境说明`
- `docker build` 类似 `npm run build`，产出可交付物
- `image` 类似前端构建产物加完整运行环境
- `container` 类似正在运行的本地 dev server 或静态资源服务
- `registry` 类似 npm 仓库，用于分发版本化产物
- `docker run -p 8080:80` 把容器内端口映射到本机浏览器可访问端口

### 常用命令

```bash
docker version                                  # 查看 Docker 客户端和服务端版本信息
docker images                                   # 查看本地已有镜像列表
docker ps                                       # 查看当前正在运行的容器
docker ps -a                                    # 查看所有容器，包括已停止的容器
docker pull node:20-alpine                      # 拉取 Node 20 的 Alpine 基础镜像
docker build -t my-vite-app .                   # 用当前目录构建镜像，并命名为 my-vite-app
docker run -d --name vite-demo -p 8080:80 my-vite-app  # 后台启动容器，把本机 8080 映射到容器 80
docker logs vite-demo                           # 查看 vite-demo 容器日志
docker exec -it vite-demo sh                    # 进入容器内部执行 shell，便于排查问题
docker stop vite-demo                           # 停止正在运行的 vite-demo 容器
docker rm vite-demo                             # 删除已经停止的 vite-demo 容器
docker rmi my-vite-app                          # 删除本地 my-vite-app 镜像
```

### Vite 入门容器化示例

项目结构：

```text
vite-demo/
├─ package.json
├─ index.html
├─ src/
├─ Dockerfile
└─ .dockerignore
```

`.dockerignore`：

```dockerignore
node_modules
dist
.git
npm-debug.log
```

`Dockerfile`：

```dockerfile
FROM node:20-alpine AS build
# 使用 Node 20 Alpine 作为构建阶段基础镜像

WORKDIR /app
# 设置容器内工作目录为 /app

COPY package*.json ./
# 先复制依赖描述文件，便于复用依赖安装缓存
RUN npm ci
# 按锁文件安装依赖，适合 CI 和生产构建

COPY . .
# 再复制项目源码
RUN npm run build
# 执行前端生产构建，输出 dist 目录

FROM nginx:1.27-alpine
# 使用轻量 Nginx 镜像作为运行阶段

COPY --from=build /app/dist /usr/share/nginx/html
# 把构建产物复制到 Nginx 静态资源目录

EXPOSE 80
# 声明容器对外提供 80 端口

CMD ["nginx", "-g", "daemon off;"]
# 前台启动 Nginx，保持容器持续运行
```

构建并运行：

```bash
docker build -t vite-demo .                     # 构建名为 vite-demo 的前端镜像
docker run -d --name vite-demo -p 8080:80 vite-demo  # 后台启动容器并映射访问端口
```

浏览器访问：

```text
http://localhost:8080
```

### 练习任务

1. 创建一个 Vite React 或 Vite Vue 项目。
2. 添加 `.dockerignore`，排除 `node_modules`、`dist`、`.git`。
3. 编写多阶段 `Dockerfile`：第一阶段使用 `node:20-alpine` 构建，第二阶段使用 `nginx:alpine` 运行。
4. 构建镜像：`docker build -t frontend-stage1 .`
5. 启动容器：`docker run -d --name frontend-stage1 -p 8080:80 frontend-stage1`
6. 用浏览器访问 `http://localhost:8080`。
7. 使用 `docker logs`、`docker ps`、`docker exec` 查看运行状态。

### 常见坑

| 问题 | 处理 |
|---|---|
| 端口映射写反 | `-p 8080:80` 表示本机 `8080` 映射到容器 `80` |
| 容器名冲突 | 执行 `docker rm -f vite-demo` 后重新启动 |
| 构建上下文过大 | 在 `.dockerignore` 排除 `node_modules`、`dist`、`.git` |
| Vite dev server 访问失败 | 使用 `vite --host 0.0.0.0` |
| Node 版本差异 | 在 Dockerfile 固定主版本，例如 `node:20-alpine` |
| 路径大小写问题 | Linux 容器严格区分大小写，组件引用路径和真实文件名保持一致 |

---

## 第 2 阶段：Docker 镜像与容器操作

![第2阶段配图](images/docker-stage-2.png)

本阶段目标：掌握镜像和容器的基本操作，能把前端构建产物放进 Nginx 容器中运行，并理解端口映射、目录挂载、日志查看和清理流程。

```mermaid
flowchart LR
  A["pull 镜像"] --> B["run 容器"]
  B --> C["映射端口"]
  C --> D["挂载目录"]
  D --> E["查看日志 / 清理"]
```

### 镜像管理

镜像是应用运行环境模板。前端开发常用镜像：

```bash
node:20
node:20-alpine
nginx:alpine
redis:7-alpine
postgres:16-alpine
```

常用命令：

```bash
docker pull nginx:alpine                        # 拉取 nginx:alpine 镜像
docker images                                   # 查看本地镜像列表
docker image ls                                 # 查看本地镜像列表，等价于 docker images
docker image inspect nginx:alpine               # 查看镜像的详细元数据
docker rmi nginx:alpine                         # 删除指定镜像
docker image prune                              # 清理悬空镜像，释放磁盘空间
```

推荐使用带版本号的镜像标签，例如 `node:20-alpine`，让本地开发、CI 构建和部署环境保持稳定。

### 容器生命周期

容器是镜像运行后的实例。一个镜像可以启动多个容器，每个容器拥有独立状态。

```bash
docker run nginx:alpine                         # 前台启动一个 Nginx 容器，便于观察默认输出
docker run -d --name web nginx:alpine          # 后台启动容器，并命名为 web
docker ps                                       # 查看当前运行中的容器
docker ps -a                                    # 查看所有容器状态
docker stop web                                 # 停止 web 容器
docker start web                                # 启动已停止的 web 容器
docker restart web                              # 重启 web 容器
docker rm web                                   # 删除已停止的 web 容器
docker logs web                                 # 查看 web 容器日志
docker logs -f web                              # 持续跟踪 web 容器日志输出
docker exec -it web sh                          # 进入 web 容器内部执行 shell
```

### 端口映射

容器内部服务运行在容器自己的端口上，宿主机通过端口映射访问容器服务。

格式：

```bash
-p 宿主机端口:容器端口
```

运行 Nginx 并映射到本地 `8080`：

```bash
docker run -d --name nginx-demo -p 8080:80 nginx:alpine  # 启动 Nginx，并把本机 8080 映射到容器 80
```

访问：

```text
http://localhost:8080
```

Vite 开发服务器在容器中运行时，监听所有网卡：

```bash
npm run dev -- --host 0.0.0.0                   # 让 Vite 监听所有网卡，宿主机浏览器才能访问容器内 dev server
```

### 数据卷与目录挂载

目录挂载把宿主机目录映射到容器目录，适合本地开发、静态资源托管和配置文件注入。

Linux/macOS：

```bash
# `--name static-site`：指定容器名称，便于后续管理
# `-p 8080:80`：把本机 8080 映射到容器 80
# `-v $(pwd)/dist:/usr/share/nginx/html`：挂载本地 dist 到 Nginx 站点目录
docker run -d --name static-site -p 8080:80 -v $(pwd)/dist:/usr/share/nginx/html nginx:alpine
```

Windows PowerShell：

```powershell
# `--name static-site`：指定容器名称，便于后续管理
# `-p 8080:80`：把本机 8080 映射到容器 80
# `-v ${PWD}/dist:/usr/share/nginx/html`：挂载当前目录下的 dist 到 Nginx 站点目录
docker run -d --name static-site -p 8080:80 -v ${PWD}/dist:/usr/share/nginx/html nginx:alpine
```

数据卷适合持久化容器数据：

```bash
docker volume create frontend-cache             # 创建名为 frontend-cache 的数据卷
docker volume ls                                # 查看本地所有数据卷
docker volume inspect frontend-cache            # 查看 frontend-cache 的详细信息
docker volume rm frontend-cache                 # 删除 frontend-cache 数据卷
```

### Nginx 托管静态站点练习

准备目录：

```text
demo-site/
  index.html
  style.css
  main.js
```

运行：

```bash
# `--name demo-site`：指定演示容器名称
# `-p 8080:80`：把本机 8080 映射到容器 80
# `-v $(pwd)/demo-site:/usr/share/nginx/html`：挂载本地 demo-site 到站点目录
docker run -d --name demo-site -p 8080:80 -v $(pwd)/demo-site:/usr/share/nginx/html nginx:alpine
```

访问：

```text
http://localhost:8080
```

### Vite dist 托管练习

```bash
npm install                                     # 安装项目依赖
npm run build                                   # 构建前端生产产物，默认输出到 dist
# `--name vite-dist`：指定容器名称
# `-p 8080:80`：把本机 8080 映射到容器 80
# `-v $(pwd)/dist:/usr/share/nginx/html`：挂载构建产物到 Nginx 目录
docker run -d --name vite-dist -p 8080:80 -v $(pwd)/dist:/usr/share/nginx/html nginx:alpine
```

SPA 路由场景需要 Nginx fallback：

```nginx
server {
  listen 80;
  server_name localhost;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

### 常见坑

| 问题 | 处理 |
|---|---|
| 端口被占用 | 更换宿主机端口，例如 `-p 8081:80` |
| 页面 404 | 检查挂载路径，确认 `dist/index.html` 存在 |
| SPA 刷新 404 | 配置 `try_files $uri $uri/ /index.html;` |
| Windows 路径问题 | PowerShell 使用 `${PWD}` |
| 容器名称冲突 | 删除旧容器或更换 `--name` |
| 镜像删除失败 | 先停止并删除依赖该镜像的容器 |

---

## 第 3 阶段：Dockerfile 与自定义镜像

![第3阶段配图](images/docker-stage-3.png)

这一阶段的目标是把前端项目推进到可稳定构建、可分发、可运行的自定义镜像。最常见的生产镜像结构是：用 Node 完成依赖安装和前端构建，用 Nginx 托管最终静态文件。

```mermaid
flowchart LR
  A["Node 构建阶段"] --> B["npm ci"]
  B --> C["npm run build"]
  C --> D["Nginx 运行阶段"]
  D --> E["dist 发布"]
```

### Dockerfile 常用指令

```dockerfile
FROM node:20-alpine
# 选择 Node 20 Alpine 作为基础镜像
WORKDIR /app
# 设置工作目录
COPY package*.json ./
# 先复制依赖清单
RUN npm ci
# 按锁文件安装依赖
COPY . .
# 复制项目源码
RUN npm run build
# 执行生产构建
CMD ["npm", "run", "dev"]
# 容器启动后默认运行开发服务器
```

| 指令 | 作用 |
|---|---|
| `FROM` | 指定基础镜像 |
| `WORKDIR` | 设置容器内工作目录 |
| `COPY` | 复制本地文件到镜像 |
| `RUN` | 构建镜像时执行命令 |
| `CMD` | 容器启动时默认执行命令 |
| `ENV` | 设置环境变量 |
| `ARG` | 设置构建参数 |
| `EXPOSE` | 声明容器服务端口 |
| `ENTRYPOINT` | 设置容器入口命令 |

### 镜像层与缓存

Dockerfile 的核心指令会生成镜像层。Docker 会按顺序复用缓存，某一层输入变化时，这一层以及后续层会重新执行。

推荐写法：

```dockerfile
COPY package*.json ./
# 先复制依赖文件，让依赖安装层更容易命中缓存
RUN npm ci
# 安装依赖

COPY . .
# 再复制业务源码
RUN npm run build
# 执行前端构建
```

业务代码变化时，`npm ci` 这一层通常可以复用缓存。依赖文件变化时，Docker 会重新安装依赖。

### `.dockerignore`

```dockerignore
node_modules
dist
build
.vite
.git
.gitignore
npm-debug.log
yarn-error.log
pnpm-debug.log
.env
.env.local
.DS_Store
```

`.dockerignore` 控制构建上下文，减少镜像构建体积并提升构建速度。

### Vite / React / Vue 构建到 Nginx

```dockerfile
FROM node:20-alpine AS build
# 构建阶段：安装依赖并生成 dist

WORKDIR /app
# 设置构建阶段工作目录

COPY package*.json ./
# 先复制依赖文件
RUN npm ci
# 安装依赖

COPY . .
# 复制源码
RUN npm run build
# 执行前端生产构建

FROM nginx:1.27-alpine
# 运行阶段：使用 Nginx 托管静态文件

COPY nginx.conf /etc/nginx/conf.d/default.conf
# 覆盖默认站点配置，支持 SPA 路由等规则
COPY --from=build /app/dist /usr/share/nginx/html
# 复制构建产物到站点目录

EXPOSE 80
# 声明对外提供 HTTP 80 端口

CMD ["nginx", "-g", "daemon off;"]
# 前台运行 Nginx 作为容器主进程
```

构建并运行：

```bash
docker build -t frontend-app:1.0 .              # 构建生产镜像，并打上 1.0 版本标签
docker run -d --name frontend-app -p 8080:80 frontend-app:1.0  # 后台启动生产容器并映射访问端口
```

### history 路由刷新配置

```nginx
server {
  listen 80;
  server_name localhost;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
  }
}
```

核心配置：

```nginx
try_files $uri $uri/ /index.html;
```

它会先查找真实文件，找不到时交给前端路由处理。

### 构建参数与环境变量

Vite 的前端变量通常在构建时注入：

```dockerfile
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build
```

构建时传入：

```bash
# `--build-arg VITE_API_BASE_URL=...`：在构建时注入前端 API 地址
# `-t frontend-app:prod`：给镜像打上生产标签
docker build --build-arg VITE_API_BASE_URL=https://api.example.com -t frontend-app:prod .
```

Vite 代码中读取：

```js
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
```

### 练习任务

1. 给一个 Vite React 或 Vite Vue 项目添加 `Dockerfile`。
2. 添加 `.dockerignore`，排除 `node_modules`、`dist`、`.git` 和本地环境文件。
3. 添加 `nginx.conf`，支持 history 路由刷新。
4. 使用多阶段构建生成生产镜像。
5. 运行容器并通过 `http://localhost:8080` 访问页面。
6. 修改源码后重新构建，观察 Docker 缓存命中情况。
7. 使用 `--build-arg` 注入 `VITE_API_BASE_URL`。
8. 使用 `docker history frontend-app:prod` 查看镜像层。

### 常见坑

| 问题 | 处理方式 |
|---|---|
| 刷新二级路由出现 404 | 配置 `try_files $uri $uri/ /index.html;` |
| 镜像构建很慢 | 先复制 `package*.json`，再执行 `npm ci` |
| 镜像体积过大 | 使用 Node + Nginx 多阶段构建 |
| 环境变量读取为空 | 使用 `VITE_API_BASE_URL` 这类 `VITE_` 前缀变量 |
| 修改 `.env` 后页面无变化 | 重新执行 `docker build` |
| Nginx 配置未生效 | 复制到 `/etc/nginx/conf.d/default.conf` |

---

## 第 4 阶段：Docker 网络与多容器协作

![第4阶段配图](images/docker-stage-4.png)

这一阶段的目标：让前端容器、Node API 容器、Redis/Postgres 容器在同一个 Docker 网络中协作，并理解浏览器访问路径和容器内部访问路径。

```mermaid
flowchart LR
  Browser["浏览器<br/>访问 localhost:5173"]
  Frontend["frontend 容器<br/>Vite Dev Server"]
  API["api 容器<br/>服务名: api<br/>端口: 3000"]
  Redis["redis/db 容器<br/>服务名: redis / db"]

  Browser -->|"localhost:5173"| Frontend
  Frontend -->|"http://api:3000"| API
  API -->|"redis:6379 或 db:5432"| Redis
```

### Docker 网络模式

- `bridge`：默认网络模式，容器之间通过 Docker 网络通信，适合本地多容器开发。
- `host`：容器直接使用宿主机网络，Linux 下常用于需要高性能或直接监听宿主机端口的场景。
- `none`：容器没有网络能力，适合隔离运行或安全测试。

前端开发中最常用的是 `bridge` 和自定义 bridge 网络。

### 自定义网络

```bash
docker network create app-net                    # 创建自定义 bridge 网络，供多个容器通信

# `--name redis`：指定 Redis 容器名称
# `--network app-net`：把 Redis 加入 app-net 网络
docker run -d --name redis --network app-net redis:7

# `--name api`：指定 API 容器名称
# `--network app-net`：把 API 加入同一个 Docker 网络
# `-p 3000:3000`：把本机 3000 映射到容器 3000
docker run -d --name api --network app-net -p 3000:3000 my-node-api
```

在 `api` 容器里访问 Redis：

```js
const redisUrl = "redis://redis:6379";
```

这里的 `redis` 是容器名，也是同一 Docker 网络里的 DNS 服务名。

### 服务名通信规则

容器内部访问另一个容器时，使用服务名：

```text
http://api:3000
redis://redis:6379
postgres://postgres:password@db:5432/app
```

浏览器访问容器服务时，使用宿主机映射端口：

```text
http://localhost:5173
http://localhost:3000
```

### 前端 + Node API + Redis/Postgres 示例

`docker-compose.yml`：

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - api
    networks:
      - app-net

  api:
    build: ./api
    ports:
      - "3000:3000"
    volumes:
      - ./api:/app
      - /app/node_modules
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgres://postgres:password@db:5432/app
    depends_on:
      - redis
      - db
    networks:
      - app-net

  redis:
    image: redis:7
    networks:
      - app-net

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - app-net

networks:
  app-net:
    driver: bridge

volumes:
  postgres-data:
```

### Vite Proxy 指向 API 服务名

`frontend/vite.config.js`：

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://api:3000",
        changeOrigin: true,
      },
    },
  },
});
```

前端代码：

```js
const res = await fetch("/api/users");
const users = await res.json();
```

### 常用命令

```bash
docker compose up --build                        # 前台启动所有服务，并在启动前重新构建镜像
docker compose up -d --build                     # 后台启动所有服务，并在启动前重新构建镜像
docker compose ps                                # 查看 Compose 管理的服务状态
docker compose logs -f frontend                  # 持续查看 frontend 服务日志
docker compose logs -f api                       # 持续查看 api 服务日志
docker compose exec frontend sh                  # 进入 frontend 容器内部执行 shell
docker compose exec api sh                       # 进入 api 容器内部执行 shell
docker compose exec frontend wget -qO- http://api:3000/api/health  # 在 frontend 容器里测试到 api 服务的网络连通性
docker network ls                                # 查看当前 Docker 网络列表
docker network inspect app_app-net               # 查看 app_app-net 网络中的容器和配置信息
docker compose down                              # 停止并删除 Compose 创建的容器和网络
docker compose down -v                           # 停止并删除容器、网络以及关联数据卷
```

### 常见坑

| 问题 | 处理 |
|---|---|
| 容器里写 `localhost:3000` | 容器访问 API 使用 `http://api:3000` |
| Vite 无法从宿主机访问 | 使用 `--host 0.0.0.0` |
| 数据库启动后 API 连接失败 | API 实现重试或 healthcheck |
| Postgres 配置改了仍用旧数据 | 清理旧 volume 后重新初始化 |
| 浏览器请求 `http://api:3000` 失败 | 浏览器访问 `localhost` 或使用 Vite proxy |
| 服务分属不同网络 | 在 compose 中显式加入同一网络 |

---

## 第 5 阶段：Docker Compose

![第5阶段配图](images/docker-stage-5.png)

前端项目进入真实开发后，通常会同时依赖前端 dev server、Node API、数据库、缓存服务。Docker Compose 用一个 `docker-compose.yml` 管理多容器开发环境，让团队成员用同一条命令启动完整项目。

```mermaid
flowchart LR
  A["docker-compose.yml"] --> B["services"]
  B --> C["network / volumes / env"]
  C --> D["docker compose up"]
  D --> E["多服务运行"]
```

### 核心概念

- `services`：定义要启动的服务，例如 `frontend`、`api`、`postgres`、`redis`
- `ports`：把容器端口映射到本机端口，例如 `5173:5173`
- `volumes`：挂载代码或持久化数据
- `networks`：让多个服务在同一个 Docker 网络中互相访问
- `env_file`：从 `.env` 文件加载环境变量
- `depends_on`：声明服务启动顺序，例如 API 依赖 PostgreSQL 和 Redis

### 示例：Vite Frontend + Node API + PostgreSQL + Redis

```yaml
services:
  frontend:
    image: node:20-alpine
    working_dir: /app
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - frontend_node_modules:/app/node_modules
    env_file:
      - ./frontend/.env
    depends_on:
      - api
    networks:
      - app_net

  api:
    image: node:20-alpine
    working_dir: /app
    command: sh -c "npm install && npm run dev"
    ports:
      - "3000:3000"
    volumes:
      - ./api:/app
      - api_node_modules:/app/node_modules
    env_file:
      - ./api/.env
    depends_on:
      - postgres
      - redis
    networks:
      - app_net

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: app_db
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: app_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app_net

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - app_net

volumes:
  frontend_node_modules:
  api_node_modules:
  postgres_data:

networks:
  app_net:
```

API 访问数据库时，主机名使用服务名：

```env
DATABASE_URL=postgresql://app_user:app_password@postgres:5432/app_db
REDIS_URL=redis://redis:6379
```

前端访问 API 时，浏览器运行在宿主机环境：

```env
VITE_API_BASE_URL=http://localhost:3000
```

### 常用命令

```bash
docker compose up                                # 前台启动全部服务，适合第一次观察启动日志
docker compose up -d                             # 后台启动全部服务
docker compose down                              # 停止并删除 Compose 创建的容器和网络
docker compose down -v                           # 停止并删除容器、网络和命名数据卷
docker compose logs -f                           # 持续查看所有服务日志
docker compose logs -f api                       # 持续查看 api 服务日志
docker compose ps                                # 查看各服务当前运行状态
docker compose restart api                       # 重启 api 服务
docker compose exec api sh                       # 进入 api 容器内部执行 shell
docker compose exec postgres psql -U app_user -d app_db  # 进入 Postgres 容器并连接 app_db 数据库
docker compose build                             # 单独构建 Compose 中定义的镜像
docker compose up --build                        # 先重建镜像，再启动所有服务
```

### 开发环境热更新挂载

Vite、React、Vue 项目需要把源码目录挂载进容器：

```yaml
volumes:
  - ./frontend:/app
  - frontend_node_modules:/app/node_modules
```

给 `node_modules` 单独使用命名 volume，可以避免宿主机和容器的依赖目录互相覆盖，尤其适合 Windows/macOS 开发环境。

Vite 监听容器外部访问：

```bash
npm run dev -- --host 0.0.0.0                   # 让开发服务器监听所有网卡，便于容器外访问
```

文件监听场景可以开启轮询：

```env
CHOKIDAR_USEPOLLING=true
```

### 练习任务

1. 新建 `frontend`，使用 Vite 创建 React 或 Vue 项目。
2. 新建 `api`，使用 Express、Fastify 或 NestJS 提供 `/health` 接口。
3. 编写 `docker-compose.yml`，包含 `frontend`、`api`、`postgres`、`redis` 四个服务。
4. 在 API 中读取 `DATABASE_URL` 和 `REDIS_URL`。
5. 在前端页面请求 `http://localhost:3000/health` 并展示结果。
6. 修改前端组件代码，确认浏览器自动热更新。
7. 修改 API 代码，确认 Node 服务自动重启。

### 常见坑

| 问题 | 处理 |
|---|---|
| 容器之间访问失败 | 使用 Compose service 名，例如 `postgres`、`redis`、`api` |
| 浏览器访问失败 | 使用 `localhost` 加映射端口 |
| Vite 无法访问 | 使用 `--host 0.0.0.0` |
| 数据被清空 | 谨慎使用 `docker compose down -v` |
| API 启动早于数据库就绪 | API 实现连接重试 |
| 热更新慢 | 减少挂载范围或使用 polling |

---

## 第 6 阶段：Docker 实战与最佳实践

![第6阶段配图](images/docker-stage-6.png)

这一阶段聚焦前端项目在真实团队中的 Docker 使用方式：构建更小、更安全、更稳定的镜像，并把镜像接入 CI/CD、部署、日志排错和日常维护流程。

```mermaid
flowchart LR
  A["代码提交"] --> B["CI 构建"]
  B --> C["镜像扫描"]
  C --> D["推送仓库"]
  D --> E["部署运行"]
  E --> F["日志排错"]
```

### 镜像体积优化

推荐做法：

- 使用 `node:alpine` 或更小的基础镜像
- 使用 `.dockerignore` 排除无关文件
- 构建产物只复制 `dist`、`build` 或服务运行所需文件
- 合并相关 `RUN` 命令，减少镜像层
- 使用 `npm ci` 保证依赖安装稳定
- 构建完成后清理包管理器缓存

示例 `.dockerignore`：

```dockerignore
node_modules
dist
build
.git
.gitignore
README.md
.env
.env.*
coverage
.vscode
.idea
```

### 多阶段构建

React/Vue/Vite 静态站点：

```dockerfile
FROM node:20-alpine AS builder
# 第一阶段：使用 Node 构建前端产物

WORKDIR /app
# 设置构建目录

COPY package*.json ./
# 复制依赖清单
RUN npm ci
# 按锁文件安装依赖

COPY . .
# 复制项目源码
RUN npm run build
# 生成 dist 静态产物

FROM nginx:1.27-alpine
# 第二阶段：使用 Nginx 运行静态站点

COPY --from=builder /app/dist /usr/share/nginx/html
# 把 dist 复制到 Nginx 站点目录

EXPOSE 80
# 声明容器使用 80 端口

CMD ["nginx", "-g", "daemon off;"]
# 以前台模式启动 Nginx
```

Node.js 服务端渲染或自定义服务：

```dockerfile
FROM node:20-alpine AS builder
# 第一阶段：构建服务端渲染或自定义 Node 服务产物

WORKDIR /app
# 设置构建阶段目录

COPY package*.json ./
# 复制依赖文件
RUN npm ci
# 安装完整依赖，支持构建

COPY . .
# 复制项目源码
RUN npm run build
# 执行构建任务

FROM node:20-alpine AS runner
# 第二阶段：准备精简运行环境

WORKDIR /app
ENV NODE_ENV=production
# 声明生产环境

COPY package*.json ./
# 复制依赖文件
RUN npm ci --omit=dev
# 仅安装生产依赖，减小镜像体积

COPY --from=builder /app/dist ./dist
# 复制构建产物
COPY --from=builder /app/server ./server
# 复制服务端运行代码

EXPOSE 3000
# 声明服务使用 3000 端口

CMD ["node", "server/index.js"]
# 启动 Node 服务
```

### 使用非 root 用户

生产容器使用普通用户运行进程，降低容器被入侵后的权限风险。

```dockerfile
FROM node:20-alpine
# 使用 Node 20 Alpine 作为运行基础镜像

WORKDIR /app
# 设置工作目录

COPY package*.json ./
# 复制依赖描述文件
RUN npm ci --omit=dev
# 只安装生产依赖

COPY . .
# 复制应用源码和运行文件

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# 创建应用运行用户和用户组
RUN chown -R appuser:appgroup /app
# 把应用目录权限交给普通用户

USER appuser
# 切换到普通用户运行应用

EXPOSE 3000
# 声明对外服务端口

CMD ["node", "server/index.js"]
# 启动 Node 应用
```

### 环境变量与 Secret

Vite 构建期变量：

```env
VITE_API_BASE_URL=https://api.example.com
VITE_APP_ENV=production
```

构建时传入：

```bash
# `--build-arg VITE_API_BASE_URL=...`：构建时注入前端 API 地址
# `-t frontend-app:latest`：给镜像打上 latest 标签
docker build --build-arg VITE_API_BASE_URL=https://api.example.com -t frontend-app:latest .
```

敏感信息处理建议：

- API Key、数据库密码、Token 放入 CI/CD Secret 或容器运行环境
- 前端打包进浏览器的变量都可能被用户看到
- 服务端密钥通过运行时环境变量注入
- Docker Compose 可使用 `env_file` 管理本地开发变量

### 日志和排错

```bash
docker ps                                       # 查看当前运行中的容器
docker ps -a                                    # 查看所有容器，包括已退出的容器
docker logs frontend-app                        # 查看 frontend-app 容器日志
docker logs -f frontend-app                     # 持续跟踪 frontend-app 日志输出
docker inspect frontend-app                     # 查看容器详细配置、网络和挂载信息
docker exec -it frontend-app sh                 # 进入 frontend-app 容器内部执行 shell
```

常见排错方向：

- 容器立即退出：检查 `CMD`、启动脚本、依赖文件
- 页面空白：检查构建产物路径、Nginx 静态目录、前端路由配置
- API 请求失败：检查 `VITE_API_BASE_URL`、跨域配置、网络连通性
- 端口无法访问：检查 `EXPOSE`、`docker run -p`、服务监听地址
- 本地正常线上异常：检查构建环境变量和生产资源路径

### CI/CD 中构建前端镜像

GitHub Actions 示例：

```yaml
name: Build Frontend Image

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Install dependencies
        run: npm ci

      - name: Run checks
        run: npm run lint && npm run build

      - name: Build image
        run: |
          # `--build-arg VITE_API_BASE_URL=...`：把前端 API 地址作为构建参数注入镜像
          # `-t ghcr.io/...:${{ github.sha }}`：使用 commit sha 作为镜像标签，便于追踪版本
          docker build --build-arg VITE_API_BASE_URL=${{ secrets.VITE_API_BASE_URL }} -t ghcr.io/${{ github.repository }}/frontend:${{ github.sha }} .

      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}
          severity: HIGH,CRITICAL
          exit-code: "1"

      - name: Push image
        run: docker push ghcr.io/${{ github.repository }}/frontend:${{ github.sha }} # 推送当前 commit 对应的前端镜像到镜像仓库
```

### 发布检查清单

- Dockerfile 使用多阶段构建
- `.dockerignore` 已排除 `node_modules`、`.git`、本地环境文件
- 生产镜像只包含运行所需文件
- 容器进程使用非 root 用户
- 前端公开变量和服务端 secret 已分离
- CI 中包含依赖安装、构建、测试或 lint
- 镜像扫描已接入流水线
- 镜像标签包含 commit sha 或版本号
- 容器日志可通过 `docker logs` 查看
- 生产环境端口、路由 fallback、API 地址已验证

### 常见坑

| 问题 | 处理 |
|---|---|
| `.env.production` 泄露敏感信息 | 前端包只放公开变量 |
| 二级路由刷新 404 | 配置 SPA fallback |
| 镜像复制了 `node_modules` | 使用 `.dockerignore` 和多阶段构建 |
| CI 构建结果漂移 | 使用 `npm ci` |
| 只有 `latest` 标签 | 使用 commit sha 或版本号 |
| API 地址仍是旧值 | 构建期变量变化后重新构建镜像 |

---

## 第 7 阶段：进阶方向：安全基础与 Kubernetes 入门衔接

![第7阶段配图](images/docker-stage-7.png)

这一阶段的目标：把 Docker 从本地开发和单机部署推进到团队级安全规范与 Kubernetes 编排思维。前端开发者需要理解镜像安全、Secret 管理、最小权限，以及 Compose 到 Kubernetes 的概念映射。

```mermaid
flowchart LR
  A["Docker Compose<br/>本地多服务"] --> B["镜像仓库<br/>Registry"]
  B --> C["Kubernetes Deployment"]
  C --> D["Pod<br/>运行容器"]
  D --> E["Service<br/>稳定访问入口"]
  E --> F["Ingress<br/>域名 / HTTPS"]
  F --> G["用户访问"]
```

### Docker 安全基础

**使用非 root 用户**

Node 服务镜像使用普通用户运行：

```dockerfile
FROM node:20-alpine
# 使用 Node 20 Alpine 作为基础镜像

WORKDIR /app
# 设置应用工作目录

COPY package*.json ./
# 复制依赖文件
RUN npm ci --omit=dev
# 安装生产依赖

COPY . .
# 复制应用源码

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# 创建非 root 用户和用户组
RUN chown -R appuser:appgroup /app
# 调整应用目录所有权

USER appuser
# 使用普通用户运行服务

EXPOSE 3000
# 声明服务端口
CMD ["node", "server/index.js"]
# 启动 Node 服务
```

**镜像扫描**

本地扫描：

```bash
docker scout quickview frontend-app:latest      # 快速查看镜像概况和基础安全信息
docker scout cves frontend-app:latest           # 扫描镜像中的已知漏洞列表
```

CI 中也可以使用 Trivy：

```bash
trivy image --severity HIGH,CRITICAL frontend-app:latest  # 扫描镜像中的高危和严重漏洞
```

**最小权限**

运行容器时减少能力：

```bash
# `--read-only`：把容器根文件系统设为只读
# `--cap-drop=ALL`：移除全部 Linux capability，降低权限
# `--security-opt no-new-privileges`：禁止进程在运行时获得更高权限
# `-p 8080:80`：把本机 8080 映射到容器 80
docker run --read-only --cap-drop=ALL --security-opt no-new-privileges -p 8080:80 frontend-app:latest
```

静态前端镜像通常只需要读取静态文件和监听 HTTP 端口。需要写入临时文件的服务，可以挂载专门的临时目录。

**Secret 管理**

前端浏览器代码里的变量都是公开信息。数据库密码、第三方服务 Token、私钥应放在服务端或平台 Secret 中。

本地 Compose：

```yaml
services:
  api:
    env_file:
      - ./api/.env.local
```

Kubernetes：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:
  DATABASE_URL: postgres://app:password@postgres:5432/app
```

### Compose 与 Kubernetes 概念映射

| Docker Compose | Kubernetes | 作用 |
|---|---|---|
| `services.frontend` | `Deployment` | 定义运行哪些容器、副本数、镜像版本 |
| `container` | `Pod` | Kubernetes 中运行容器的最小调度单元 |
| `ports` | `Service` | 给 Pod 提供稳定访问入口 |
| `volumes` | `PersistentVolumeClaim` | 持久化数据 |
| `env_file` / `environment` | `ConfigMap` / `Secret` | 管理配置和敏感信息 |
| Compose 默认网络 | Cluster DNS | 服务名解析 |
| 反向代理 | `Ingress` | 域名、路径、HTTPS 入口 |

### 前端静态站点部署例子

生产镜像：

```dockerfile
FROM node:20-alpine AS build
# 构建阶段：安装依赖并生成前端 dist

WORKDIR /app
# 设置构建目录
COPY package*.json ./
# 复制依赖文件
RUN npm ci
# 安装依赖
COPY . .
# 复制源码
RUN npm run build
# 执行前端生产构建

FROM nginx:1.27-alpine
# 运行阶段：使用 Nginx 提供静态资源
COPY nginx.conf /etc/nginx/conf.d/default.conf
# 复制自定义 Nginx 配置
COPY --from=build /app/dist /usr/share/nginx/html
# 复制构建产物
EXPOSE 80
# 声明服务端口
CMD ["nginx", "-g", "daemon off;"]
# 前台启动 Nginx
```

Kubernetes Deployment：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: registry.example.com/frontend:1.0.0
          ports:
            - containerPort: 80
```

Service：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
```

Ingress：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: frontend
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

### API 网关部署思路

前端静态资源由 Nginx 提供，API 通过网关或 Ingress 路由到后端：

```text
https://app.example.com/        -> frontend service
https://app.example.com/api/*   -> api service
```

Ingress 可以按路径转发：

```yaml
paths:
  - path: /
    pathType: Prefix
    backend:
      service:
        name: frontend
        port:
          number: 80
  - path: /api
    pathType: Prefix
    backend:
      service:
        name: api
        port:
          number: 3000
```

### 后续学习路线

1. 熟练 Dockerfile 多阶段构建和 Compose 多服务开发环境。
2. 学习镜像扫描、非 root 用户、Secret 管理、最小权限运行。
3. 学习 Kubernetes 基础对象：Pod、Deployment、Service、Ingress、ConfigMap、Secret。
4. 用 `kind` 或 Docker Desktop Kubernetes 在本地部署一个前端镜像。
5. 学习 Helm 或 Kustomize，管理多环境配置。
6. 学习日志、监控、滚动发布、回滚和资源限制。

### 练习任务

1. 给第 6 阶段的前端镜像添加非 root 用户。
2. 使用 Trivy 或 Docker Scout 扫描镜像。
3. 把 Compose 中的 `frontend` 服务改写成 Kubernetes `Deployment` 和 `Service`。
4. 使用本地 Kubernetes 部署前端镜像。
5. 配置 Ingress，把 `/` 指向前端，把 `/api` 指向 Node API。
6. 把 API 的数据库连接字符串放入 Kubernetes Secret。
7. 为前端 Deployment 设置副本数 `replicas: 2`，观察滚动更新。

### 常见坑

| 问题 | 处理 |
|---|---|
| 把前端变量当作 Secret | 浏览器可见变量只放公开配置 |
| 镜像标签使用 `latest` | 使用版本号或 commit sha |
| 容器用 root 运行 | Dockerfile 增加普通用户并切换 `USER` |
| Pod 访问数据库失败 | 使用 Kubernetes Service 名和正确 namespace |
| Ingress 路由异常 | 检查 path、service name、service port |
| ConfigMap 修改后应用未更新 | 触发 Deployment 滚动更新 |
| 静态站点刷新 404 | Nginx 配置 SPA fallback |

建议学习节奏：先把本地 Compose 环境跑顺，再把前端生产镜像部署到 Kubernetes，最后补齐安全扫描、Secret、Ingress 和滚动发布。
