# Caddy 安装与反向代理配置教程（适用于 Debian/Ubuntu）

本教程将指导你如何在 Debian/Ubuntu 系统中安装 Caddy，并配置一个简单的反向代理站点。

---

## 📦 安装前置依赖

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
```

---

## 🔑 添加 Caddy 官方 GPG 密钥与软件源

```bash
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
```

---

## 🔄 更新软件包并安装 Caddy

```bash
sudo apt update
sudo apt install caddy
```

---

## ⚙️ 配置反向代理

> 请将 `sub.xxxxx.xyz` 替换为你自己的域名。

```bash
cat << EOF > /etc/caddy/Caddyfile
sub.xxxxx.xyz {
    reverse_proxy 127.0.0.1:3001
    }
EOF
```

---

## 🛡️ 启动 Caddy 服务并设置自启动

```bash
sudo systemctl enable --now caddy
```

---

## 🔁 修改配置后的重载命令

```bash
sudo systemctl reload caddy
```

---

## 🔧 常用管理命令

- 启动：

```bash
sudo systemctl start caddy
```

- 停止：

```bash
sudo systemctl stop caddy
```

- 重启：

```bash
sudo systemctl reload caddy
```

- 查看状态：

```bash
systemctl status caddy
```

---

## 📌 注意事项

- 请确保你的域名已正确解析到本机公网 IP。
- 默认使用 80/443 端口，请确保未被其他程序占用。
- Caddy 将自动申请 HTTPS 证书，无需手动设置。

---

## 📚 参考资料

- [Caddy 官方文档](https://caddyserver.com/docs/)
- [Cloudsmith 仓库说明](https://dl.cloudsmith.io/public/caddy/stable/)

---

## 🧑‍💻 作者说明

本项目仅用于学习参考，欢迎提交 Issue 或 PR。
