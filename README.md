# ComfyUI Palette Recolor（色卡重着色）

用预设色卡对图像重新配色，支持 [Coolors](https://coolors.co) 链接或十六进制色值。适配 ComfyUI 1.23.x。

**网页版体验（无需安装）**： [https://quhan0925.github.io/ComfyUI-PaletteRecolor/](https://quhan0925.github.io/ComfyUI-PaletteRecolor/)

## 安装

1. 进入 ComfyUI 自定义节点目录：
   ```bash
   cd ComfyUI/custom_nodes
   ```
2. 克隆本仓库：
   ```bash
   git clone https://github.com/你的用户名/ComfyUI-PaletteRecolor.git
   ```
3. 重启 ComfyUI。

**依赖**：仅使用 Python 标准库与 ComfyUI 自带的 `torch`，无需额外安装。

## 节点说明

### Palette Recolor（色卡重着色）

- **image**：输入图像（来自 Load Image 等）
- **palette**：色卡，支持两种写法：
  - **Coolors 链接**：直接粘贴整段链接，例如  
    `https://coolors.co/e8c547-30323d-3f414f-4d5061-5c80bc-cdd1c4`
  - **十六进制色值**：用逗号、空格或横线分隔，例如  
    `e8c547,30323d,3f414f,4d5061,5c80bc,cdd1c4` 或 `#e8c547 #30323d ...`

输出为按该色卡重新着色后的图像，会尽量保持原图的明暗与区域感。

### Parse Palette（解析色卡预览）

- **palette**：同上，Coolors 链接或十六进制字符串
- **height**：预览条高度（像素）

输出一张色条预览图，便于检查色卡是否正确解析。

## 使用方式

1. 在 [Coolors](https://coolors.co) 生成或选好一套配色，复制浏览器地址栏链接。
2. 在 ComfyUI 中接好「Load Image」等节点得到图像，再接入 **Palette Recolor (色卡重着色)**。
3. 在 **palette** 输入框粘贴 Coolors 链接或一串十六进制色值。
4. 运行工作流即可得到按该色卡重着色后的图像。

## 原理简述

对输入图像做 k-means 聚类得到若干主色，按亮度与色卡颜色一一对应，再把每个像素映射到最近的聚类并替换为对应色卡颜色，从而在保留大致明暗与区域结构的前提下统一成色卡配色。

## 网页版公网部署（GitHub Pages）

仓库内 `docs/` 目录为网页版测试页，可通过 GitHub Pages 发布为公网链接。

1. 在 GitHub 打开本仓库，进入 **Settings** → **Pages**。
2. **Source** 选择 **Deploy from a branch**。
3. **Branch** 选 `main`，**Folder** 选 **/docs**，点击 **Save**。
4. 等待一两分钟后，访问：  
   **https://quhan0925.github.io/ComfyUI-PaletteRecolor/**  
   即可使用网页版色卡重着色（上传图片、输入色卡、查看效果）。  
   若你的仓库名为其他或为 fork，将链接中的 `quhan0925` 和 `ComfyUI-PaletteRecolor` 换成你的用户名和仓库名即可。

## 许可证

MIT
