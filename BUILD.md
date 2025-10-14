# 万年历本地版 - 构建指南

## 📋 构建工具说明

本项目提供了两个构建脚本，方便你快速重新构建应用：

| 脚本文件 | 用途 | 说明 |
|---------|------|------|
| **`build.sh`** | 完整构建 | 首次构建或完整重建 |
| **`quick_build.sh`** | 快速重建 | 代码修改后快速重新打包 |

## 🚀 使用方法

### 首次构建

```bash
./build.sh
```

- ✅ 自动创建虚拟环境
- ✅ 安装所有依赖
- ✅ 下载 AppImage 工具
- ✅ 完整构建 AppImage 分发包

### 快速重建（代码修改后）

```bash
./quick_build.sh
```

- ⚡ 假设虚拟环境已存在
- ⚡ 快速清理和重新构建
- ⚡ 适合开发阶段的频繁测试

## 🔧 构建脚本选项

### build.sh 支持的选项

```bash
# 显示帮助信息
./build.sh --help

# 仅清理构建文件
./build.sh --clean-only

# 跳过清理步骤（更快）
./build.sh --skip-clean
```

## 📦 构建输出

成功构建后，会生成以下分发包：

```
万年历本地版-x86_64.AppImage  # 主程序 (~65MB)
install.sh                    # 安装脚本 (~6KB)
wannianli-icon.png            # 备用图标 (~13KB)
README_用户安装指南.md        # 用户文档 (~3KB)
```

## 🧪 测试构建结果

```bash
# 1. 测试 AppImage 直接运行
./万年历本地版-x86_64.AppImage

# 2. 测试安装脚本
./install.sh

# 3. 在开始菜单中查找应用
#    （应该在应用菜单中显示正确图标）
```

## 📁 Git 忽略文件

已配置的 `.gitignore` 会忽略以下构建相关文件：

- `build/`, `dist/` - PyInstaller 构建目录
- `*.spec` - PyInstaller 配置文件
- `appimage/squashfs-root/` - AppImage 提取文件
- `appimage/*.AppImage` - 生成的 AppImage 文件
- `appimage/WanNianLi.AppDir/` - AppDir 目录
- `venv/` - Python 虚拟环境
- `wannianli-icon.png` - 构建时复制的图标

## 🔄 开发工作流

1. **修改代码**：
   ```bash
   # 编辑 main.py 或其他源文件
   vim main.py
   ```

2. **快速测试**：
   ```bash
   # 快速重建
   ./quick_build.sh

   # 测试运行
   ./万年历本地版-x86_64.AppImage
   ```

3. **发布准备**：
   ```bash
   # 完整重建（确保干净）
   ./build.sh

   # 测试安装
   ./install.sh
   ```

4. **打包分发**：
   ```bash
   # 创建分发压缩包
   tar -czf wannianli-$(date +%Y%m%d).tar.gz \
       万年历本地版-x86_64.AppImage \
       install.sh \
       wannianli-icon.png \
       README_用户安装指南.md
   ```

## 🛠️ 故障排除

### 常见问题

**Q: 构建失败，提示找不到 Python**
```bash
# 确保安装了 Python 3
python3 --version

# 如果没有，安装 Python 3
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Q: AppImage 无法运行**
```bash
# 检查架构
uname -m
# 应该输出: x86_64

# 设置可执行权限
chmod +x 万年历本地版-x86_64.AppImage
```

**Q: 图标不显示**
```bash
# 重新运行安装脚本
./install.sh

# 或手动安装图标
mkdir -p ~/.local/share/icons/hicolor/256x256/apps
cp wannianli-icon.png ~/.local/share/icons/hicolor/256x256/apps/wannianli.png
```

**Q: 完全重新构建**
```bash
# 清理所有文件
./build.sh --clean-only

# 完整重建
./build.sh
```

## 📝 系统要求

- **操作系统**: Linux (Ubuntu 18.04+, Mint 19+, Fedora 30+)
- **架构**: x86_64
- **Python**: 3.8+
- **网络**: 首次构建需要下载 AppImage 工具

## 🎯 自定义构建

如需自定义构建选项，可以修改：

1. **PyInstaller 选项**: 编辑 `build.sh` 中的 `pyinstaller` 命令
2. **AppImage 设置**: 修改 AppDir 配置文件
3. **图标和名称**: 更新 `icon.png` 和相关配置

---

**构建愉快！** 🎉