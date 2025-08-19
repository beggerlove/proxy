# Snell Server 一键安装脚本

本脚本用于在 Linux 系统上一键安装、更新或卸载 Snell Server，支持 amd64 和 aarch64 架构。

## 功能特性

- 一键安装 Snell Server
- 支持自定义端口、密码、HTTP 混淆
- 支持卸载与更新 Snell Server
- 自动生成 systemd 服务

## 依赖环境

请确保系统已安装以下依赖：

- wget
- curl
- unzip
- openssl

如未安装，脚本会提示安装,然后请你手动安装。

## 使用方法

### 1. 一键安装

```bash
bash <(curl -sSLf "https://raw.githubusercontent.com/beggerlove/proxy/master/snell/snell.sh")
```

根据提示输入端口、密码、是否开启 HTTP 混淆等信息。

### 3. 卸载 Snell Server

```bash
bash <(curl -sSLf "https://raw.githubusercontent.com/beggerlove/proxy/master/snell/snell.sh") uninstall
```

### 4. 更新 Snell Server

自动更新到最新版本：

```bash
bash <(curl -sSLf "https://raw.githubusercontent.com/beggerlove/proxy/master/snell/snell.sh") update
```

指定版本更新（如 v4.0.1）：

```bash
bash <(curl -sSLf "https://raw.githubusercontent.com/beggerlove/proxy/master/snell/snell.sh") update v4.0.1
```

## 参数说明

- 监听端口：可自定义，默认 8964
- 密码：可自定义，留空则自动生成
- HTTP 混淆：可选，Y/N，默认不开启

## 输出信息

安装完成后，脚本会输出如下信息：

- 端口
- 密码
- 混淆方式
- 版本

## 配置与服务文件

- 配置文件路径：`/etc/snell-server.conf`
- systemd 服务文件：`/etc/systemd/system/snell.service`

可通过如下命令管理 Snell 服务：

```bash
systemctl start snell.service
systemctl stop snell.service
systemctl restart snell.service
```

## PS

 **自用脚本更新维护随意**


## 参考链接

- [Snell 官方文档](https://manual.nssurge.com/others/snell.html)

---
