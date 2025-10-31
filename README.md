# 万年历本地版

一个功能丰富的离线中文万年历应用，基于 PySide6 开发，支持公历/农历显示、节假日查询、宜忌查看等功能。

![应用预览](icon.png)
![应用预览](imagesimple.png)

## ✨ 主要特性

- 📅 **双历显示** - 完整的公历和农历信息对照
- 🎉 **节假日查询** - 法定节假日和传统节日显示
- ⚖️ **宜忌查看** - 每日宜忌事项查询
- 📋 **假期导入** - 支持文本导入官方假期安排
- 🎨 **现代界面** - 美观的用户界面设计
- 🚀 **系统托盘** - 支持最小化到系统托盘
- 🔧 **开机启动** - 支持开机自动启动和静默启动
- 📦 **跨发行版** - AppImage 格式支持所有主流 Linux 发行版

## 🚀 快速开始

### 用户安装

1. **下载分发包文件**：
   - `万年历本地版-x86_64.AppImage` (~64MB)
   - `install.sh` (~6KB)
   - `wannianli-icon.png` (~13KB) [可选]
   - `README_用户安装指南.md` (~3KB) [可选]

2. **一键安装**：
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **启动应用**：
   - 在应用菜单中搜索"万年历本地版"
   - 或直接运行：`~/.local/bin/万年历本地版.AppImage`

### 直接运行

```bash
chmod +x 万年历本地版-x86_64.AppImage
./万年历本地版-x86_64.AppImage
```

## 🔧 开发环境

### 系统要求

- **操作系统**: Linux (Ubuntu 18.04+, Mint 19+, Fedora 30+)
- **架构**: x86_64 (Intel/AMD 64位)
- **Python**: 3.8+
- **依赖**: 见 requirements.txt

### 依赖包

```bash
PySide6>=6.0.0
lunar-python>=0.2.0
```

### 首次构建

```bash
# 克隆仓库
git clone <repository-url>
cd OfflineCalendar

# 完整构建
./build.sh
```

### 开发重建

```bash
# 代码修改后快速重建
./quick_build.sh

# 测试运行
./万年历本地版-x86_64.AppImage
```

## 📁 项目结构

```
OfflineCalendar/
├── main.py                              # 主程序源码
├── requirements.txt                     # Python 依赖
├── icon.png                            # 应用图标
├── user_holidays.json                  # 用户假期数据存储
├── install.sh                          # 自动安装脚本
├── build.sh                            # 完整构建脚本
├── quick_build.sh                      # 快速重建脚本
├── README_用户安装指南.md               # 用户安装文档
├── BUILD.md                            # 构建指南
├── PROJECT_SUMMARY.md                  # 项目总结
├── test_silent_start.py                # 静默启动测试
├── 万年历本地版-x86_64.AppImage         # 分发包（构建生成）
└── wannianli-icon.png                   # 备用图标（构建生成）
```

## 🎯 核心功能

### 日历显示
- **月视图**: 清晰的月历网格布局
- **日期选择**: 点击日期查看详细信息
- **今日高亮**: 当前日期特殊标记
- **周末标识**: 周末日期颜色区分

### 农历信息
- **农历日期**: 完整的农历年月日显示
- **节气信息**: 二十四节气自动标注
- **干支纪年**: 天干地支和生肖显示
- **传统节日**: 春节、中秋、端午等节日

### 节假日管理
- **法定假期**: 元旦、春节、国庆等法定假日
- **调休安排**: 工作日和休息日调整
- **假期导入**: 支持粘贴官方放假安排文本
- **自定义假期**: 用户可添加特殊日期

### 宜忌查询
- **每日宜忌**: 基于传统黄历的宜忌事项
- **详细显示**: 左侧面板完整信息展示
- **快速参考**: 日常生活决策参考

### 系统集成
- **系统托盘**: 最小化到托盘运行
- **开机启动**: 支持开机自动启动
- **静默启动**: 开机后后台静默运行
- **桌面集成**: 开始菜单和桌面图标

## 🛠️ 技术架构

### GUI 框架
- **PySide6**: 基于 Qt6 的现代 GUI 框架
- **布局管理**: 响应式布局，支持窗口缩放
- **样式表**: QSS 样式表定制界面外观
- **信号槽**: 事件驱动编程模式

### 农历计算
- **lunar-python**: 专业的农历计算库
- **节气算法**: 精确的二十四节气计算
- **节日数据**: 内置传统和法定节日数据
- **宜忌算法**: 基于传统历法的宜忌计算

### 数据持久化
- **JSON 存储**: 用户假期数据本地存储
- **配置文件**: QSettings 应用配置管理
- **路径管理**: 跨平台路径处理

### 打包分发
- **PyInstaller**: Python 应用打包工具
- **AppImage**: Linux 跨发行版分发格式
- **自动化脚本**: 一键构建和安装脚本

## 📱 界面截图

### 主界面
- 左侧详情面板：显示选中日期的详细信息
- 右侧日历网格：月视图日历显示
- 顶部控制栏：年月选择和功能按钮

### 功能区域
- **日期导航**: 年份月份选择器，今天按钮
- **假日选择**: 法定节假日快速跳转
- **假期管理**: 导入官方假期安排
- **托盘菜单**: 系统托盘右键菜单

## 🔌 配置说明

### 开机启动配置
应用支持两种开机启动模式：

1. **正常启动**: 开机后显示主窗口
2. **静默启动**: 开机后最小化到托盘

配置方法：右键托盘图标 → 开机启动/静默启动

### 假期导入格式
支持导入官方发布的假期安排文本，格式示例：
```
春节：2月10日至17日放假调休，共8天。2月4日（星期日）、2月18日（星期日）上班。
清明节：4月5日放假，与周末连休。
劳动节：5月1日至5日放假调休，共5天。4月28日（星期日）、5月11日（星期六）上班。
```

### 数据存储位置
- **用户配置**: `~/.config/OfflineCalendar/`
- **假期数据**: `~/.config/OfflineCalendar/user_holidays.json`
- **安装文件**: `~/.local/bin/万年历本地版.AppImage`
- **桌面文件**: `~/.local/share/applications/wannianli.desktop`
- **图标文件**: `~/.local/share/icons/hicolor/256x256/apps/wannianli.png`

## 🗂️ 文件说明

### 构建脚本

| 脚本 | 功能 | 使用场景 |
|------|------|----------|
| `build.sh` | 完整构建 | 首次构建、环境设置、完整重建 |
| `quick_build.sh` | 快速重建 | 开发阶段频繁测试 |
| `install.sh` | 自动安装 | 用户一键安装到系统 |

### 构建脚本选项

`build.sh` 支持的选项：
```bash
# 显示帮助信息
./build.sh --help

# 仅清理构建文件
./build.sh --clean-only

# 跳过清理步骤（更快）
./build.sh --skip-clean
```

## 🔧 故障排除

### 常见问题

**Q: AppImage 无法运行？**
```bash
# 检查架构
uname -m
# 应输出: x86_64

# 设置可执行权限
chmod +x 万年历本地版-x86_64.AppImage
```

**Q: 图标不显示？**
```bash
# 重新运行安装脚本
./install.sh

# 或手动更新图标缓存
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor/
```

**Q: 开机启动不工作？**
- 检查桌面文件是否正确安装：`ls ~/.config/autostart/`
- 确认 AppImage 路径是否正确
- 查看系统日志：`journalctl --user -u offlinecalendar.desktop`

**Q: 托盘图标不显示？**
- 检查系统是否支持托盘：需要安装 `libappindicator3-1`
- Ubuntu/Debian: `sudo apt install libappindicator3-1`
- Fedora: `sudo dnf install libappindicator-gtk3`

**Q: 构建失败？**
```bash
# 完全清理重建
./build.sh --clean-only
./build.sh

# 检查 Python 版本
python3 --version  # 需要 3.8+

# 检查依赖
pip3 list | grep -E "(PySide6|lunar-python)"
```

## 📊 性能特性

- **启动速度**: < 3秒冷启动
- **内存占用**: ~50MB 运行时内存
- **文件大小**: ~64MB AppImage 包
- **响应性能**: 毫秒级界面响应

## 🌟 版本历史

### v1.0 (当前版本)
- ✅ 基础日历功能
- ✅ 农历和节假日显示
- ✅ 宜忌查询
- ✅ 假期导入功能
- ✅ 系统托盘支持
- ✅ 开机启动功能
- ✅ AppImage 打包分发

### 未来计划
- [ ] 节日提醒功能
- [ ] 主题切换支持
- [ ] 数据导出功能
- [ ] 国际化支持
- [ ] ARM64 架构支持
- [ ] 自动更新机制

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

### 代码规范
- Python 代码遵循 PEP 8 规范
- 使用有意义的变量和函数名
- 添加必要的注释和文档字符串
- 确保代码通过测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [PySide6](https://doc.qt.io/qtforpython/) - 现代 GUI 框架
- [lunar-python](https://github.com/6tail/lunar-python) - 农历计算库
- [AppImage](https://appimage.org/) - Linux 应用分发格式
- [PyInstaller](https://www.pyinstaller.org/) - Python 打包工具

## 📞 技术支持

如遇到问题或有功能建议，请：

1. 查看 [BUILD.md](BUILD.md) 构建指南
2. 查看 [README_用户安装指南.md](README_用户安装指南.md) 用户文档
3. 提交 Issue 到项目仓库
4. 提供详细的错误信息和系统环境

---

**享受使用万年历本地版！** 🌙📅

*最后更新: 2025-10-14*
