# Emby反代教程


## 使用方法

### 1. 安装 Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

### 2. 安装 Certbot（如果你还没有证书）

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 3. 获取证书（换成你自己的域名）

```bash
sudo certbot certonly --nginx -d 你的域名
```
证书默认存放路径：
	•	/etc/letsencrypt/live/你的域名/fullchain.pem
	•	/etc/letsencrypt/live/你的域名/privkey.pem

你配置里的路径要改成这两个。

手动测试自动续签：
```bash
sudo certbot renew --dry-run
```


### 4. 写配置文件
上传配置文件将 Nginx.conf 放入服务器的 `/etc/nginx/sites-available/`

### 5. 建立软链接

```bash
sudo ln -s /etc/nginx/sites-available/embyNginx.conf /etc/nginx/sites-enabled/
```

### 6. 测试并重载 Nginx
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 7. 其他命令

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```
