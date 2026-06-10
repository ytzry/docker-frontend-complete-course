# 面向前端开发者的 Docker 教程站点

这个仓库用于维护一份面向前端开发者的 Docker 教程，并通过 `Mdtht` 主题把 Markdown 自动渲染为 HTML，再发布到 GitHub Pages。

## 仓库说明

- 教程源码：`docker-frontend-complete-course.md`
- 页面渲染脚本：`scripts/render_mdtht.py`
- 渲染依赖：`requirements-render.txt`
- `Mdtht` 主题资源：`vendor/mdtht/`
- GitHub Actions 工作流：`.github/workflows/render-mdtht.yml`

当前仓库只跟踪源码和渲染脚本：

- `index.html` 不进入 Git
- `site/` 是本地预览或 CI 构建产物目录
- GitHub Pages 直接部署 workflow 生成的 artifact

## 本地生成

先安装依赖：

```bash
pip install -r requirements-render.txt
```

生成 HTML：

```bash
python scripts/render_mdtht.py docker-frontend-complete-course.md site/index.html --asset-prefix ./
```

如果需要本地完整预览，再把静态资源复制到 `site/`：

```bash
mkdir -p site/images site/vendor
cp -R images/. site/images/
cp -R vendor/. site/vendor/
```

生成后的页面入口是 `site/index.html`。

## 自动部署

仓库已经配置 GitHub Actions 自动部署：

1. 提交 `*.md`、渲染脚本或 `vendor/mdtht/` 资源变更
2. workflow 生成 `site/index.html`
3. workflow 复制 `images/` 和 `vendor/` 到 `site/`
4. workflow 上传 `site/` 为 GitHub Pages artifact
5. GitHub Pages 直接部署这份 artifact

这条流程只部署一次，不会再把生成产物提交回仓库。

## 目录结构

```text
.
├─ .github/workflows/
├─ images/
├─ scripts/
├─ vendor/mdtht/
├─ docker-frontend-complete-course.md
├─ requirements-render.txt
└─ README.md
```

## 依赖说明

- Python 3.12 或更高版本
- `Markdown==3.7`
- `highlight.js` 和 `mermaid` 通过 CDN 注入到生成页面
- `Mdtht` 使用 vendored 静态资源，来源分支：`ytzry/Mdtht@fix-issue-12`
