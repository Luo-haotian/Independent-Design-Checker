# KIMI API 设置指南

## ❌ 错误来源

你目前访问的是 **KIMI 网页版** (kimi.com)
- 这是给普通用户聊天用的
- 生成的 Key 不能用于 API 调用

## ✅ 正确步骤

### 1. 访问 API 平台
打开：https://platform.moonshot.cn/

### 2. 注册/登录
- 使用手机号注册
- 完成实名认证（需要身份证）

### 3. 获取 API Key
1. 登录后点击左侧 **"API Key 管理"**
2. 点击 **"创建 API Key"**
3. 输入名称（如：IDC-Project）
4. 复制生成的 Key（格式：`sk-...`）

### 4. 充值（新用户有免费额度）
- 新用户通常有 15元 免费额度
- 或点击 "充值" 添加余额

### 5. 更新到项目
将新的 Key 粘贴到 `.env` 文件：
```
KIMI_API_KEY=sk-你的新key
```

## 🔍 区别说明

| 平台 | URL | 用途 |
|------|-----|------|
| KIMI 网页版 | kimi.com | 普通聊天 |
| Moonshot API | platform.moonshot.cn | 开发者 API |

## 📞 帮助

如果遇到问题：
1. 查看文档：https://platform.moonshot.cn/docs
2. 联系客服：平台右下角在线客服
