# 第 5 阶段：Docker Compose

![第5阶段配图](../images/docker-stage-5.png)

这一阶段解决的问题是：当你的前端项目同时依赖 API、Postgres、Redis 时，怎样用一份配置把整个开发环境稳定拉起来，并且让团队成员拿到仓库后直接运行。

对前端团队来说，Docker Compose 的价值很直接：

- 用一份 `compose.yaml` 管理多个服务
- 统一开发环境版本，减少“我本地能跑”的问题
- 让前端、后端、数据库、缓存的启动方式固定下来
- 把端口、挂载、环境变量、服务依赖写成可审查的配置

## 1. 先建立正确概念

Docker Compose 是多容器应用的编排配置工具。你可以把它理解成“多条 `docker run` 命令的结构化版本”，但它的表达能力更强，适合长期维护。

一个前端全栈开发环境常见会有这几类服务：

- `web`：Vite / React / Vue 开发服务器
- `api`：Node.js / Express / NestJS 接口服务
- `postgres`：数据库
- `redis`：缓存或队列辅助服务

这几个服务的关系通常是：

- 浏览器访问宿主机暴露出来的前端端口
- 前端开发服务器在容器内把 API 请求转发到 `api` 服务
- `api` 服务通过 Docker 内部网络访问 `postgres` 和 `redis`

```mermaid
flowchart LR
    Browser["浏览器<br/>http://localhost:5173"] --> HostPort["宿主机端口 5173"]
    HostPort --> Web["web 容器<br/>Vite Dev Server"]
    Web --> Api["api 容器<br/>Node.js API"]
    Api --> Pg["postgres 容器<br/>5432"]
    Api --> Redis["redis 容器<br/>6379"]
```

## 2. Compose 文件结构

Compose 默认读取这些文件名之一：

- `compose.yaml`
- `compose.yml`
- `docker-compose.yml`
- `docker-compose.yaml`

推荐直接用 `compose.yaml`，它是当前官方文档更常见的写法。

一个常见结构如下：

```yaml
services:
  web:
    ...
  api:
    ...
  postgres:
    ...
  redis:
    ...

volumes:
  postgres-data:
  redis-data:
  web-node-modules:
  api-node-modules:

networks:
  app-network:
```

每一部分的职责：

- `services`：定义具体运行的容器服务
- `volumes`：定义命名卷，用来持久化数据或隔离依赖目录
- `networks`：定义容器之间的网络

## 3. 一份准确的前端开发示例

下面这份 Compose 示例覆盖 React/Vue + Node API + Postgres + Redis 的本地开发环境。

```yaml
services:
  web:
    image: node:20-alpine
    container_name: frontend-web
    working_dir: /app
    ports:
      - "5173:5173"
    volumes:
      - .:/app
      - web-node-modules:/app/node_modules
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    env_file:
      - .env.web
    depends_on:
      - api
    networks:
      - app-network

  api:
    image: node:20-alpine
    container_name: frontend-api
    working_dir: /app
    ports:
      - "3000:3000"
    volumes:
      - ./server:/app
      - api-node-modules:/app/node_modules
    command: sh -c "npm install && npm run dev"
    env_file:
      - .env.api
    depends_on:
      - postgres
      - redis
    networks:
      - app-network

  postgres:
    image: postgres:16-alpine
    container_name: frontend-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppass
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    container_name: frontend-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - app-network

volumes:
  postgres-data:
  redis-data:
  web-node-modules:
  api-node-modules:

networks:
  app-network:
    driver: bridge
```

这份配置里有几个关键点：

- `web` 用 `.:/app` 把当前前端项目挂载进容器，代码改动能即时同步
- `web-node-modules:/app/node_modules` 单独做成命名卷，避免宿主机目录覆盖容器里的依赖
- `api` 和 `web` 分别维护自己的 `node_modules`
- `postgres-data` 和 `redis-data` 是持久化数据卷，容器删掉后数据仍可保留
- 所有服务都加入 `app-network`，因此容器之间可以直接用服务名通信

## 4. services：每个服务都在描述什么

`services` 是 Compose 的核心。

以 `web` 服务为例：

```yaml
web:
  image: node:20-alpine
  working_dir: /app
  ports:
    - "5173:5173"
  volumes:
    - .:/app
    - web-node-modules:/app/node_modules
  command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
  env_file:
    - .env.web
  depends_on:
    - api
```

这些字段的作用：

- `image`：使用哪个镜像作为运行环境
- `working_dir`：容器内默认工作目录
- `ports`：宿主机端口映射到容器端口
- `volumes`：挂载代码目录或持久化目录
- `command`：容器启动后执行的命令
- `env_file`：从外部文件注入环境变量
- `depends_on`：表达服务启动顺序关系

## 5. volumes：为什么前端项目一定要讲清楚挂载

前端项目里最容易踩坑的部分就是挂载。

### 5.1 热更新挂载

```yaml
volumes:
  - .:/app
```

这行的意思是：把宿主机当前目录挂载到容器内 `/app`。

好处：

- 你在本地改 `src/App.tsx`
- 容器内文件同步变化
- Vite dev server 能检测到变更并热更新

### 5.2 为什么还要单独挂 `node_modules`

如果只写这一条：

```yaml
volumes:
  - .:/app
```

宿主机项目目录会完整覆盖容器内 `/app`。这时如果宿主机没有正确的 `node_modules`，或者宿主机依赖和容器 Linux 环境不兼容，容器内依赖就会出问题。

更稳定的写法是：

```yaml
volumes:
  - .:/app
  - web-node-modules:/app/node_modules
```

这表示：

- 源码来自宿主机挂载
- `node_modules` 保存在 Docker 命名卷里
- 容器内依赖与宿主机系统解耦

这个写法对 Windows 和 macOS 很重要，因为很多依赖带有平台差异，尤其是原生模块和文件监听行为。

### 5.3 数据卷和源码挂载的区别

- `.:/app`：绑定挂载，适合源码开发
- `postgres-data:/var/lib/postgresql/data`：命名卷，适合数据库数据持久化

## 6. networks：容器之间如何互相访问

同一个 Compose 项目中的服务，默认可以通过服务名互相访问；显式定义网络后，结构更清晰，也方便后续扩展。

例如：

- `web` 容器内访问 API：`http://api:3000`
- `api` 容器内访问 Postgres：`postgres://appuser:apppass@postgres:5432/appdb`
- `api` 容器内访问 Redis：`redis://redis:6379`

重点：

- 浏览器不能直接解析 `api` 这个 Docker 服务名
- 浏览器访问的是宿主机地址，比如 `http://localhost:5173`
- 容器访问容器才使用服务名

```mermaid
flowchart TD
    A["浏览器"] --> B["localhost:5173"]
    B --> C["web 服务"]
    C --> D["http://api:3000"]
    D --> E["postgres:5432"]
    D --> F["redis:6379"]
```

## 7. depends_on：它解决启动顺序，不解决服务就绪

`depends_on` 表示 Compose 会按顺序启动容器，例如先启动 `postgres`、`redis`，再启动 `api`。

```yaml
api:
  depends_on:
    - postgres
    - redis
```

这个配置表达的是“先把数据库和缓存容器拉起来”，但它不保证：

- Postgres 已经初始化完成
- Redis 已经开始接受连接
- API 第一次连接一定成功

因此在真实项目里，你还需要：

- 给 API 做重试连接逻辑
- 或者增加健康检查与等待机制

学习阶段先把顺序概念讲清楚就够了。上线阶段要把“容器启动”和“服务可用”分开理解。

## 8. env_file：怎样给服务注入环境变量

`env_file` 用来从文件加载环境变量。

示例：

```yaml
web:
  env_file:
    - .env.web

api:
  env_file:
    - .env.api
```

`.env.web` 可以这样写：

```env
VITE_API_BASE_URL=/api
```

`.env.api` 可以这样写：

```env
PORT=3000
DATABASE_URL=postgres://appuser:apppass@postgres:5432/appdb
REDIS_URL=redis://redis:6379
```

这里要分清两类变量：

- 前端构建期或开发期变量：例如 `VITE_API_BASE_URL`
- API 运行期变量：例如数据库连接串、Redis 地址

浏览器端变量默认不属于 secret。数据库密码、服务 token 这类内容应放在后端服务环境变量中。

## 9. 前端代理配置要写对

当前端运行在 `web` 容器里时，Vite 代理的目标地址通常写成 Docker 服务名：

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

原因很简单：

- 浏览器发请求到 `http://localhost:5173/api/users`
- 请求先到 `web` 容器里的 Vite dev server
- Vite 再把请求代理到 `http://api:3000`

这里的 `api` 是容器网络里的服务名，Vite 能解析它，因为 Vite 跑在容器里。

## 10. 常用命令与中文注释

### 10.1 启动整个项目

```bash
docker compose up -d  # 按 compose.yaml 启动所有服务，并在后台运行
```

### 10.2 前台查看启动日志

```bash
docker compose up  # 前台启动所有服务，直接在当前终端查看日志输出
```

### 10.3 停止并删除容器

```bash
docker compose down  # 停止并删除当前 Compose 项目创建的容器、默认网络
```

### 10.4 连同数据卷一起删除

```bash
docker compose down -v  # 停止并删除容器，同时删除命名卷，数据库数据也会清空
```

### 10.5 查看服务状态

```bash
docker compose ps  # 查看 Compose 项目下每个服务的运行状态和端口映射
```

### 10.6 查看某个服务日志

```bash
docker compose logs web  # 查看 web 服务日志
docker compose logs api  # 查看 api 服务日志
```

### 10.7 持续跟踪日志

```bash
docker compose logs -f web  # 持续跟踪 web 服务日志，适合观察热更新和报错
docker compose logs -f api  # 持续跟踪 api 服务日志，适合排查接口和数据库连接问题
```

### 10.8 进入容器内部

```bash
docker compose exec web sh  # 进入 web 容器的 shell，检查依赖、配置、源码挂载情况
docker compose exec api sh  # 进入 api 容器，排查接口服务运行状态
```

### 10.9 重新构建并启动

```bash
docker compose up -d --build  # 重新构建镜像并启动服务，适合 Dockerfile 或依赖变更后使用
```

### 10.10 单独启动某个服务

```bash
docker compose up -d postgres  # 单独启动 postgres 服务
docker compose up -d redis     # 单独启动 redis 服务
```

### 10.11 查看命名卷

```bash
docker volume ls  # 查看当前 Docker 环境中的所有数据卷
```

### 10.12 查看网络

```bash
docker network ls  # 查看当前 Docker 网络列表
```

## 11. 一套更适合前端仓库的目录示例

```text
project-root/
├─ compose.yaml
├─ .env.web
├─ .env.api
├─ package.json
├─ src/
├─ vite.config.ts
└─ server/
   ├─ package.json
   └─ src/
```

如果前后端在同一个仓库里，这种结构比较常见。前端根目录是 `web`，后端代码放在 `server/`。

## 12. Windows 和 macOS 常见问题

### 12.1 文件监听延迟或热更新不生效

表现：

- 改了前端代码，浏览器不刷新
- HMR 很慢
- 容器内文件变化没有被 Vite 监听到

处理方式：

```ts
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    watch: {
      usePolling: true,
    },
  },
})
```

`usePolling: true` 会增加 CPU 消耗，但在 Docker Desktop + Windows/macOS 文件共享环境下通常更稳定。

### 12.2 `node_modules` 被宿主机覆盖

表现：

- 容器里执行过 `npm install`
- 启动时仍提示缺少依赖
- 某些原生模块报平台错误

原因通常是只挂了 `.:/app`，没有单独处理 `/app/node_modules`。

建议固定采用：

```yaml
volumes:
  - .:/app
  - web-node-modules:/app/node_modules
```

### 12.3 行尾和脚本执行问题

表现：

- `sh: not found`
- shell 脚本执行失败
- 容器里脚本出现奇怪的格式错误

原因通常是 Windows 的 CRLF 行尾导致。

建议：

- Shell 脚本统一使用 LF
- Git 配置里明确处理行尾规则
- 启动脚本尽量简短，复杂逻辑放到可控脚本文件中

### 12.4 端口冲突

表现：

- `5173`、`3000`、`5432`、`6379` 被本机已有程序占用

处理方式：

```bash
docker compose ps  # 查看服务当前端口映射
```

然后修改 `compose.yaml`：

```yaml
ports:
  - "5174:5173"
```

这表示宿主机访问 `5174`，容器内服务仍监听 `5173`。

## 13. 排错思路

### 13.1 浏览器打不开前端页面

按这个顺序排查：

1. 看容器是否启动

```bash
docker compose ps  # 检查 web 服务是否处于 Up 状态
```

2. 看前端日志

```bash
docker compose logs web  # 查看 Vite 是否成功启动，端口是否正确
```

3. 看 Vite 是否监听 `0.0.0.0`

```bash
docker compose exec web sh  # 进入 web 容器
```

然后检查启动命令和配置。

### 13.2 前端能打开，但接口请求失败

按这个顺序排查：

1. 确认 `api` 服务是否启动

```bash
docker compose ps  # 检查 api 服务状态
```

2. 查看 API 日志

```bash
docker compose logs api  # 查看接口服务报错、端口监听和数据库连接情况
```

3. 检查 Vite 代理配置是否写成 `http://api:3000`

4. 在 `web` 容器里测试能否访问 `api`

```bash
docker compose exec web sh  # 进入 web 容器，进一步做网络连通性检查
```

### 13.3 API 起不来

常见原因：

- 依赖未安装成功
- `DATABASE_URL` 配错
- `postgres` 容器已启动，但数据库还没准备好
- `node_modules` 被宿主机挂载覆盖

重点检查：

```bash
docker compose logs api       # 查看 API 启动日志
docker compose logs postgres  # 查看数据库初始化日志
docker compose logs redis     # 查看 Redis 启动情况
```

### 13.4 数据库数据异常

如果你想重置学习环境，可以明确删除数据卷：

```bash
docker compose down -v  # 停止服务并删除命名卷，适合重置数据库和缓存数据
```

这条命令会清空 `postgres-data` 和 `redis-data`，执行前要确认你不需要保留数据。

## 14. 一个适合教学的逐步练习

### 练习 1：只启动前端服务

目标：

- 用 Compose 启动一个 Vite 项目
- 通过 `localhost:5173` 访问
- 修改源码后确认热更新生效

### 练习 2：接入 API 服务

目标：

- 增加 `api` 服务
- 配置 Vite proxy 到 `http://api:3000`
- 从前端发一个 `/api/health` 请求并看到返回结果

### 练习 3：接入 Postgres 和 Redis

目标：

- 为 API 注入 `DATABASE_URL` 和 `REDIS_URL`
- API 启动后成功连上数据库和缓存
- 用日志验证依赖服务地址走的是 Docker 服务名

### 练习 4：验证数据持久化

目标：

- 在 Postgres 中写入一条测试数据
- 执行 `docker compose down`
- 再执行 `docker compose up -d`
- 确认数据仍然存在

### 练习 5：重置整个环境

目标：

- 执行 `docker compose down -v`
- 重新启动服务
- 确认数据库被重置

## 15. 常见误区

### 误区 1：`depends_on` 表示服务已经可用

正确理解：

- `depends_on` 解决启动顺序
- 可用性要看健康检查、连接重试、服务初始化时间

### 误区 2：浏览器也可以访问 `http://api:3000`

正确理解：

- `api` 是 Docker 内部服务名
- 浏览器访问的是宿主机地址或前端代理地址

### 误区 3：`node_modules` 直接跟源码一起挂载就够了

正确理解：

- 前端源码适合绑定挂载
- `node_modules` 更适合独立命名卷

### 误区 4：`docker compose down` 会删除数据库数据

正确理解：

- 默认不会删除命名卷
- 只有加 `-v` 才会一起删除卷数据

## 16. 学完这一阶段，你应该掌握什么

你需要能独立完成这些动作：

- 写出一个包含 `web`、`api`、`postgres`、`redis` 的 `compose.yaml`
- 解释 `services`、`volumes`、`networks`、`depends_on`、`env_file` 的职责
- 解释前端热更新挂载和 `node_modules` 命名卷的必要性
- 说明浏览器、前端容器、API 容器、数据库之间的访问路径
- 用 `docker compose logs`、`docker compose ps`、`docker compose exec` 做基本排错

这一阶段打稳之后，你再去写完整本地开发环境、联调环境和 CI/CD 发布流程，配置会清晰很多。
