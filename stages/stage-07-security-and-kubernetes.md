# 第 7 阶段：安全基础与 Kubernetes 衔接

![第7阶段配图](../images/docker-stage-7.png)

这一阶段解决两个问题：

1. 前端项目的容器怎样运行得更安全。
2. 本地 `Docker Compose` 项目怎样平滑迁移到 `Kubernetes`。

你在前端团队里最常见的交付物有三类：

- `Vite / React / Vue` 构建后的静态站点
- `Node.js` BFF 或 SSR 服务
- 一组通过 `/api` 访问后端接口的 Web 应用

这三类项目都会经过同一条链路：`源码 -> Docker 镜像 -> 镜像仓库 -> Kubernetes 部署 -> Service 暴露 -> Ingress 路由`。这一阶段的目标，是把这条链路的安全和部署逻辑彻底讲清楚。

## 学习目标

- 理解镜像扫描、最小权限、非 root、只读文件系统、Secret 管理的实际作用
- 学会判断哪些配置适合放进前端构建变量，哪些必须留在服务端或平台 Secret
- 准确理解 `Compose service`、`Pod`、`Deployment`、`Service`、`Ingress` 的职责边界
- 能把一个前端静态站点和一个 `/api` 后端服务部署到 Kubernetes
- 能识别这一阶段最容易误导新手的配置错误

## 总体流程图

```mermaid
flowchart LR
  A["前端源码<br/>React / Vue / Vite"] --> B["Docker 多阶段构建"]
  B --> C["镜像扫描<br/>漏洞与配置检查"]
  C --> D["镜像仓库<br/>Registry"]
  D --> E["Kubernetes Deployment"]
  E --> F["Pod"]
  F --> G["Service"]
  G --> H["Ingress"]
  H --> I["浏览器访问域名"]
  H --> J["/api 路由到后端服务"]
```

## 1. 前端容器安全基础

很多团队把“能跑起来”当成容器交付完成。上线环境更关心四件事：

- 镜像里有没有已知漏洞
- 容器是不是用 root 在跑
- 进程有没有超出业务需要的写权限
- 密钥和密码有没有混进镜像或前端产物

### 1.1 镜像扫描

镜像扫描的目标是尽早发现：

- 基础镜像里的系统漏洞
- Node 依赖里的高危包
- 明显的配置风险

常见做法：

- 本地开发阶段扫描基础镜像和应用依赖
- CI 阶段对最终产出的镜像做一次完整扫描
- 对 `critical` 和 `high` 风险设置阻断规则

以 `Trivy` 为例：

```bash
docker build -t frontend-prod:1.0.0 .         # 构建前端生产镜像，标签是 frontend-prod:1.0.0
trivy image frontend-prod:1.0.0               # 扫描这个镜像中的系统包、Node 依赖和漏洞信息
trivy image --severity HIGH,CRITICAL frontend-prod:1.0.0  # 只关注高危和严重漏洞
```

判断扫描结果时看三点：

- 漏洞是不是出现在最终运行镜像里
- 有没有可升级的安全版本
- 这个包是不是生产环境真正会加载

前端项目常见误区：

- 扫描 `builder` 阶段很严格，最终运行镜像反而没扫
- 只看 `npm audit`，完全没看基础镜像里的 Alpine、Debian 包
- 看到漏洞数量很多就直接忽略，没有建立阻断阈值

### 1.2 最小权限

最小权限的意思是：容器只拿业务运行必需的权限。

前端静态站点场景通常只需要：

- 监听一个 HTTP 端口
- 读取静态文件
- 写日志到标准输出

它通常不需要：

- root 身份
- 任意目录写权限
- 访问 Docker Socket
- 特权模式

最小权限要落到几个具体配置上：

- 使用非 root 用户
- 只挂载业务需要的目录
- 容器文件系统尽量只读
- 临时文件写到单独的可写挂载点

### 1.3 非 root 运行

root 运行的风险很直接：应用进程一旦被利用，攻击面更大，容器内可操作的资源更多。

前端静态站点适合用非 root 用户运行。下面是一个更稳妥的多阶段 `Dockerfile` 示例：

```dockerfile
# 第一阶段：构建前端产物
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 第二阶段：提供静态文件
FROM nginx:1.27-alpine

# 复制构建结果到 Nginx 静态目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义 nginx 配置，监听 8080 端口，方便非 root 运行
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 创建非 root 用户和组，固定 uid/gid 便于平台对齐权限
RUN addgroup -g 1001 -S appgroup \
    && adduser -S appuser -u 1001 -G appgroup \
    && chown -R appuser:appgroup /usr/share/nginx/html /var/cache/nginx /var/run /etc/nginx/conf.d

USER 1001:1001

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

配套的 `nginx.conf` 需要把端口改成非特权端口：

```nginx
server {
  listen 8080;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

这里有两个关键点：

- Linux 里 `1024` 以下端口通常需要更高权限，前端容器直接用 `8080` 更稳
- 容器里是 `8080`，Kubernetes `Service` 或 `Ingress` 对外再映射成 `80` 或 `443`

验证当前容器是否以非 root 身份运行：

```bash
docker run --rm frontend-prod:1.0.0 id        # 在临时容器里执行 id 命令，查看当前用户 uid 和 gid
docker run --rm frontend-prod:1.0.0 whoami    # 查看当前容器进程用户名
```

期望结果：

- `uid` 不是 `0`
- 用户名不是 `root`

### 1.4 只读文件系统

前端静态站点容器非常适合只读文件系统，因为它的主要职责是读取构建产物并返回给浏览器。

只读文件系统的价值：

- 降低运行时篡改文件的风险
- 提前暴露代码对本地写入的隐性依赖
- 让镜像行为更稳定，方便排障

Docker 运行示例：

```bash
docker run -d --name frontend-ro -p 8080:8080 --read-only frontend-prod:1.0.0  # 用只读根文件系统启动前端容器
```

如果应用必须写临时文件，可以显式提供可写目录：

```bash
docker run -d --name frontend-ro \
  -p 8080:8080 \
  --read-only \
  --tmpfs /tmp \
  frontend-prod:1.0.0                            # 只开放 /tmp 为临时可写内存文件系统
```

在 Kubernetes 中对应的安全配置写在 `securityContext`：

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  runAsGroup: 1001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

字段作用：

- `runAsNonRoot: true`：要求容器进程必须以非 root 启动
- `allowPrivilegeEscalation: false`：禁止进程再提升权限
- `readOnlyRootFilesystem: true`：把容器根文件系统设为只读
- `capabilities.drop: [ALL]`：移除默认 Linux 能力，减少额外权限

### 1.5 Secret 管理

这一节最容易被前端新手误解。

前端浏览器里可见的变量，本质上都是公开信息。只要它被打进前端 JS 包或者出现在浏览器请求里，用户就能看到。

因此你要做这样的区分：

适合放进前端构建变量的内容：

- 公开 API 域名
- 站点名称
- 埋点上报地址
- 第三方公开 key 中设计为浏览器侧公开的那一类

必须放进服务端或平台 Secret 的内容：

- 数据库密码
- JWT 签名密钥
- 私有 API Token
- 云服务 Access Key
- 支付签名私钥

本地 Compose 常见写法：

```yaml
services:
  api:
    image: my-api:1.0.0
    env_file:
      - .env.local
```

这里的 `env_file` 只是本地开发便利方案。它不等于真正的 Secret 管理系统，也不适合把明文密钥长期留在仓库周边目录。

Kubernetes `Secret` 示例：

```bash
kubectl create secret generic api-secret \
  --from-literal=DATABASE_URL='postgres://app:password@postgres:5432/appdb' \
  --from-literal=JWT_SECRET='replace-with-real-secret'   # 在集群中创建名为 api-secret 的 Secret
```

在 Pod 里注入 Secret：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: my-api:1.0.0
          ports:
            - containerPort: 3000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: api-secret
                  key: DATABASE_URL
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: api-secret
                  key: JWT_SECRET
```

更稳的团队实践：

- Secret 来源交给 CI/CD 或云平台密钥系统
- 开发环境和生产环境使用不同 Secret
- 不把 `.env.production` 直接打包进镜像
- 不把真正的后端凭证暴露给前端构建

## 2. Compose 到 Kubernetes 的概念映射

很多教程把 `Compose` 和 `Kubernetes` 说成“两个语法不同的部署工具”。这个说法太浅，容易让人迁移时配错对象边界。

更准确的理解是：

- `Compose` 解决单机或少量主机上的多容器编排
- `Kubernetes` 解决集群级调度、服务发现、滚动发布、自愈和权限控制

### 2.1 概念对照表

| Docker Compose | Kubernetes | 作用 |
| --- | --- | --- |
| `service` | `Deployment` + `Service` | 一个负责定义运行副本和更新策略，一个负责提供稳定访问入口 |
| `container` | `Pod` 中的容器 | 容器仍然是镜像运行实例，K8s 以 Pod 为最小调度单元 |
| `docker compose up --scale` | `replicas` | 控制服务副本数 |
| `ports` | `containerPort` + `Service port` | 容器端口与集群访问端口需要分层定义 |
| `environment` | `ConfigMap` / `Secret` / `env` | 普通配置与敏感配置分开管理 |
| `volume` | `PersistentVolumeClaim` / `emptyDir` / `configMap` volume | 把不同类型的数据挂载到容器 |
| 默认网络和服务名解析 | Cluster DNS | 服务通过 `service-name` 相互访问 |
| 反向代理 | `Ingress` | 负责域名、HTTPS、路径分发 |

### 2.2 映射流程图

```mermaid
flowchart TD
  A["Compose service: frontend"] --> B["Kubernetes Deployment: frontend"]
  B --> C["Pod: frontend 容器副本"]
  C --> D["Service: frontend-svc"]
  D --> E["Ingress: / 指向前端"]

  F["Compose service: api"] --> G["Kubernetes Deployment: api"]
  G --> H["Pod: api 容器副本"]
  H --> I["Service: api-svc"]
  I --> J["Ingress: /api 指向后端"]
```

### 2.3 你需要抓住的边界

`Deployment` 负责：

- 运行多少个副本
- 用哪个镜像版本
- 滚动升级如何进行
- Pod 挂了怎样自动补齐

`Service` 负责：

- 给一组 Pod 一个稳定名字
- 在集群内部做服务发现
- 把流量转发给健康的 Pod

`Ingress` 负责：

- 域名接入
- HTTPS 终止
- 路径路由，如 `/`、`/api`

新手最常见错误是把三者混成一个概念，结果会出现：

- 只有 `Deployment`，没有 `Service`，集群里其他服务无法稳定访问
- 只有 `Service`，没有 `Ingress`，浏览器无法按域名和路径进入
- 在 `Ingress` 里直接写 Pod 端口理解，忽略 `Service` 端口层

## 3. 从 Compose 前端项目迁移到 Kubernetes

先看一个典型的 Compose 项目：

```yaml
services:
  frontend:
    image: my-frontend:1.0.0
    ports:
      - "8080:8080"
    depends_on:
      - api

  api:
    image: my-api:1.0.0
    ports:
      - "3000:3000"
    environment:
      PORT: 3000
      DATABASE_URL: postgres://app:password@postgres:5432/appdb

  postgres:
    image: postgres:16-alpine
```

迁移到 Kubernetes 后，职责拆分会更细：

- `frontend Deployment`
- `frontend Service`
- `api Deployment`
- `api Service`
- `postgres StatefulSet` 或托管数据库
- `Ingress`
- `Secret` / `ConfigMap`

生产环境里，数据库更常见的选择是云数据库服务。课程里仍然展示容器化数据库，是为了帮助你理解网络和配置边界。

## 4. 前端静态站点部署实战

这一节用一个最常见场景来讲：

- React/Vue/Vite 构建后生成 `dist`
- Nginx 在容器里托管静态资源
- `/api` 请求转发给 Node API 服务
- 浏览器统一访问一个域名

### 4.1 前端 Deployment

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
          image: my-frontend:1.0.0
          ports:
            - containerPort: 8080
          securityContext:
            runAsNonRoot: true
            runAsUser: 1001
            runAsGroup: 1001
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

说明：

- `replicas: 2`：前端有两个副本，提升可用性
- `containerPort: 8080`：容器里的 Nginx 监听 8080
- `emptyDir: {}`：给临时目录提供可写空间，配合只读根文件系统

应用部署命令：

```bash
kubectl apply -f frontend-deployment.yaml      # 把前端 Deployment 提交到当前 Kubernetes 集群
kubectl get pods -l app=frontend               # 按标签查看前端 Pod 状态
kubectl describe pod -l app=frontend           # 查看 Pod 事件，排查镜像拉取或探针失败
```

### 4.2 前端 Service

`Service` 给前端 Pod 提供一个稳定入口，供 Ingress 转发流量。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-svc
spec:
  selector:
    app: frontend
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

这里的端口关系要说清楚：

- `targetPort: 8080`：流量最终进容器 8080
- `port: 80`：集群里其他对象访问 `frontend-svc` 时用 80

查看 Service：

```bash
kubectl apply -f frontend-service.yaml         # 创建或更新前端 Service
kubectl get svc frontend-svc                   # 查看前端 Service 暴露的集群端口
```

### 4.3 API Deployment 与 Service

后端 API 需要独立部署，因为它有自己的镜像、变量、扩缩容策略和日志。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: my-api:1.0.0
          ports:
            - containerPort: 3000
          env:
            - name: PORT
              value: "3000"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: api-secret
                  key: DATABASE_URL
          securityContext:
            runAsNonRoot: true
            runAsUser: 1001
            runAsGroup: 1001
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-svc
spec:
  selector:
    app: api
  ports:
    - name: http
      port: 3000
      targetPort: 3000
```

部署后端：

```bash
kubectl apply -f api-deployment.yaml           # 创建或更新 API Deployment
kubectl apply -f api-service.yaml              # 创建或更新 API Service
kubectl get endpoints api-svc                  # 查看 api-svc 当前关联到了哪些 Pod IP
```

### 4.4 Ingress 与 `/api` 路由

这一段必须准确，因为很多新手会把前端路由、Nginx 反向代理、Ingress 路由混在一起。

在 Kubernetes 里，最清晰的做法是：

- 前端静态资源由 `frontend-svc` 提供
- `/api` 路径由 `api-svc` 提供
- 浏览器请求统一打到同一个域名

Ingress 示例：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-svc
                port:
                  number: 3000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-svc
                port:
                  number: 80
```

路由逻辑：

- `https://app.example.com/` 进入前端静态站点
- `https://app.example.com/api/users` 进入后端 API 服务

应用 Ingress：

```bash
kubectl apply -f ingress.yaml                  # 创建或更新 Ingress 规则
kubectl get ingress                            # 查看当前命名空间中的 Ingress
kubectl describe ingress web-ingress           # 查看域名、路径和后端 Service 映射详情
```

### 4.5 浏览器侧 API 地址如何配置

这也是前端项目最常见的误区之一。

如果你已经通过 Ingress 把 `/api` 路径转发到后端，浏览器端就可以直接用相对路径：

```ts
fetch('/api/users') // 浏览器访问当前域名下的 /api/users，由 Ingress 转发到 api-svc
```

这个写法的好处：

- 同域部署更简单
- 避免额外 CORS 配置
- 开发、测试、生产的切换成本更低

如果你把前端代码写成：

```ts
fetch('http://api-svc:3000/users')
```

浏览器会失败，因为：

- `api-svc` 是 Kubernetes 集群内部 DNS 名称
- 浏览器运行在用户电脑上，不在集群网络里

准确原则：

- 浏览器访问对外域名或相对路径
- 集群内服务之间访问 `service name`

## 5. 常用命令清单

下面这组命令覆盖第 7 阶段最常用的安全与部署检查动作。

```bash
docker build -t my-frontend:1.0.0 .           # 构建前端生产镜像
docker run --rm my-frontend:1.0.0 id          # 检查容器默认用户，确认不是 root
docker run -d -p 8080:8080 --read-only my-frontend:1.0.0  # 用只读根文件系统运行前端容器
trivy image my-frontend:1.0.0                 # 扫描镜像中的漏洞和依赖风险
kubectl apply -f frontend-deployment.yaml     # 部署前端 Deployment
kubectl apply -f frontend-service.yaml        # 部署前端 Service
kubectl apply -f api-deployment.yaml          # 部署后端 Deployment
kubectl apply -f api-service.yaml             # 部署后端 Service
kubectl apply -f ingress.yaml                 # 部署入口路由规则
kubectl get pods                              # 查看当前命名空间里的 Pod
kubectl get svc                               # 查看当前命名空间里的 Service
kubectl get ingress                           # 查看当前命名空间里的 Ingress
kubectl logs deploy/api                       # 查看 api Deployment 当前 Pod 的日志
kubectl describe pod <pod-name>               # 查看指定 Pod 的事件与状态详情
```

## 6. 常见坑

### 6.1 前端变量当成 Secret

错误理解：

- 把 `VITE_API_URL`、`NEXT_PUBLIC_*`、`PUBLIC_*` 当成保密信息

准确做法：

- 公开配置可以进入前端构建
- 真正敏感数据只进入服务端或平台 Secret

### 6.2 非 root 之后应用起不来

常见原因：

- Nginx 还在监听 80
- 静态目录权限没给到运行用户
- 容器启动过程要写某个目录，结果根文件系统只读

排查顺序：

```bash
docker run --rm my-frontend:1.0.0 id          # 检查默认用户身份
docker run --rm my-frontend:1.0.0 ls -l /usr/share/nginx/html  # 查看静态目录权限
docker logs <container-id>                    # 查看容器启动失败日志
```

### 6.3 Ingress 配置了，页面还是 404

常见原因：

- `frontend-svc` 名字写错
- `service port` 配错成容器端口理解
- 前端静态服务没配置 SPA 路由回退，刷新子路由时报 404

前端单页应用要确认 Nginx 有这段配置：

```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```

### 6.4 `/api` 路由通了，浏览器仍然跨域

常见原因：

- 前端代码里写死了完整 API 域名
- 本应走同域 `/api`，结果请求打到了另一个源

建议：

- 前后端统一走同域 Ingress
- 浏览器请求优先使用相对路径

### 6.5 只读文件系统导致 Node 服务异常

Node API、SSR 服务比纯静态站点更容易碰到写文件需求，例如：

- 临时缓存
- 文件上传中转
- 运行时生成文件

做法：

- 先识别真实写入路径
- 只为必要目录挂 `emptyDir` 或持久卷
- 保持其余根文件系统只读

## 7. 练习

### 练习 1：检查前端镜像权限

任务：

1. 把你当前前端项目的生产镜像改成非 root 运行。
2. 让 Nginx 监听 `8080`。
3. 用 `docker run --rm <image> id` 验证 uid。

验收标准：

- 容器能正常启动
- `uid` 不是 `0`
- 浏览器能访问首页

### 练习 2：启用只读根文件系统

任务：

1. 用 `--read-only` 启动前端容器。
2. 观察是否有目录写入报错。
3. 如果需要，为临时目录补充 `--tmpfs /tmp` 或 Kubernetes `emptyDir`。

验收标准：

- 应用启动正常
- 页面资源可访问
- 容器日志里没有写文件权限错误

### 练习 3：把 Compose 前端迁移成 Kubernetes 对象

任务：

1. 把 `frontend` 服务改写成 `Deployment` 和 `Service`。
2. 把 `api` 服务改写成 `Deployment` 和 `Service`。
3. 用 `Ingress` 实现 `/` 到前端，`/api` 到后端。

验收标准：

- 浏览器能打开首页
- `fetch('/api/health')` 返回正常
- 前端不直接访问集群内部域名

### 练习 4：把后端数据库连接改成 Secret

任务：

1. 创建 `api-secret`。
2. 让 API Deployment 从 `secretKeyRef` 读取 `DATABASE_URL`。
3. 删除镜像或明文配置里的数据库密码。

验收标准：

- API 可以正常连接数据库
- Pod 环境变量来源于 Secret
- 镜像内容里不包含数据库明文密码

## 8. 阶段结论

这一阶段你要形成三个稳定判断：

1. 前端容器的安全基线是：扫描镜像、非 root、最小权限、只读文件系统、敏感信息不进前端构建。
2. `Compose service` 迁移到 Kubernetes 时，通常会拆成 `Deployment`、`Service`、`Ingress`、`ConfigMap`、`Secret` 等多个对象。
3. 浏览器访问域名和相对路径，集群内部服务访问 `Service` 名称，这条边界必须一直保持清晰。

掌握这一阶段之后，你已经具备把前端项目从本地 Docker 环境推进到团队级容器平台的基础能力。
