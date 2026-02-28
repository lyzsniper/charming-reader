# 🔧 完全清理重启指南

## 问题：文件已更新但浏览器仍显示旧错误

这是由于多层缓存导致的：
1. Vite服务器缓存
2. 浏览器缓存
3. React热重载缓存

## ✅ 完全清理步骤

### 步骤1：运行清理脚本

```powershell
cd frontend
.\clean-restart.ps1
```

或手动执行：

```powershell
# 停止所有node进程
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force

# 清理缓存
Remove-Item -Recurse -Force node_modules\.vite
Remove-Item -Recurse -Force dist
```

### 步骤2：重启开发服务器

```bash
pnpm run dev
```

### 步骤3：完全刷新浏览器

1. 打开浏览器开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

或快捷键：
- Windows: `Ctrl + Shift + R` 或 `Ctrl + F5`
- Mac: `Cmd + Shift + R`

### 步骤4：验证

检查浏览器控制台应该没有错误，左侧边栏应该显示6个按钮。

## 🎯 如果仍然不工作

### 核选项：完全重建

```powershell
cd frontend

# 删除node_modules
Remove-Item -Recurse -Force node_modules

# 删除lock文件
Remove-Item pnpm-lock.yaml

# 重新安装
pnpm install

# 启动
pnpm run dev
```

### 检查文件编码

```powershell
# 文件应该存在且大小正确
Get-Item src\services\agentSkillsApi.ts | Select-Object Name, Length

# 输出应该显示约 10KB
```

## ✅ 成功标志

当一切正常时，你应该看到：
- ✅ 开发服务器启动无错误
- ✅ 浏览器控制台无错误
- ✅ 左侧边栏有6个图标
- ✅ 可以点击 ✨ 和 🎛️ 图标

---

**问题应该已解决！如果还有问题，请告诉我具体的错误信息。**
