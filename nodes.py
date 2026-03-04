"""
色卡重着色节点：根据预设色卡对输入图像重新配色。
支持 Coolors 链接 (如 https://coolors.co/e8c547-30323d-3f414f-4d5061-5c80bc-cdd1c4)
或十六进制色值（逗号/空格/横线分隔）。
"""

import re
import torch


def parse_palette(palette_str: str) -> list[tuple[float, float, float]]:
    """
    从字符串解析色卡，返回 RGB 元组列表，每通道 0~1。
    支持：
    - Coolors URL: https://coolors.co/e8c547-30323d-3f414f-...
    - 十六进制: e8c547,30323d 或 #e8c547 #30323d 或 e8c547-30323d
    """
    s = palette_str.strip()
    # 从 Coolors URL 提取：/ 或 ? 后的 hex 段
    if "coolors.co" in s.lower():
        match = re.search(r"coolors\.co[/\-]([\w\-]+)", s, re.I)
        if match:
            s = match.group(1)
    # 统一分隔符：只保留 hex 字符和分隔
    s = s.replace(",", " ").replace("-", " ").replace("#", " ")
    parts = s.split()
    colors = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 允许 6 位或 8 位 hex（忽略 alpha）
        if len(p) == 6 and all(c in "0123456789abcdefABCDEF" for c in p):
            r = int(p[0:2], 16) / 255.0
            g = int(p[2:4], 16) / 255.0
            b = int(p[4:6], 16) / 255.0
            colors.append((r, g, b))
        elif len(p) == 8:
            r = int(p[0:2], 16) / 255.0
            g = int(p[2:4], 16) / 255.0
            b = int(p[4:6], 16) / 255.0
            colors.append((r, g, b))
    return colors


def luminance(r: float, g: float, b: float) -> float:
    """相对亮度 (sRGB)."""
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _kmeans_assign(pixels: torch.Tensor, centers: torch.Tensor) -> torch.Tensor:
    """pixels [N,3], centers [k,3] -> 每个像素最近的 center 索引 [N]"""
    # [N,1,3] - [1,k,3] -> [N,k,3] -> norm -> [N,k]
    d = (pixels.unsqueeze(1) - centers.unsqueeze(0)).pow(2).sum(dim=2)
    return d.argmin(dim=1)


def recolor_image(image: torch.Tensor, palette_rgb: list[tuple[float, float, float]]) -> torch.Tensor:
    """
    image: [B,H,W,3] 0~1 float
    palette_rgb: list of (r,g,b) 0~1
    用 k-means 聚类图像主色，再按亮度将聚类中心映射到色卡，重着色后保持区域感。
    """
    if not palette_rgb:
        return image
    device = image.device
    dtype = image.dtype
    B, H, W, C = image.shape
    k = len(palette_rgb)

    # 色卡按亮度排序
    palette_sorted = sorted(palette_rgb, key=lambda c: luminance(c[0], c[1], c[2]))
    palette_t = torch.tensor(palette_sorted, device=device, dtype=dtype)  # [k,3]

    out = []
    for b in range(B):
        img = image[b]  # [H,W,3]
        pixels = img.reshape(-1, 3)  # [N,3]
        n = pixels.shape[0]

        # 下采样以加速 k-means（最多约 50k 像素）
        max_pts = 50000
        if n > max_pts:
            perm = torch.randperm(n, device=device)[:max_pts]
            sample = pixels[perm]
        else:
            sample = pixels

        # 初始化：按亮度分位数选 k 个点作为初始中心
        lum = (
            0.2126 * sample[:, 0] + 0.7152 * sample[:, 1] + 0.0722 * sample[:, 2]
        )
        order = torch.argsort(lum)
        step = max(1, sample.shape[0] // k)
        centers = sample[order[step // 2 :: step][:k]]  # [k,3]
        if centers.shape[0] < k:
            centers = torch.cat(
                [centers, centers[-1:].expand(k - centers.shape[0], 3)], dim=0
            )

        # 少量迭代
        for _ in range(8):
            assign = _kmeans_assign(sample, centers)
            for i in range(k):
                mask = assign == i
                if mask.any():
                    centers[i] = sample[mask].mean(dim=0)

        # 将聚类中心按亮度排序，与色卡一一对应
        center_lum = (
            0.2126 * centers[:, 0] + 0.7152 * centers[:, 1] + 0.0722 * centers[:, 2]
        )
        center_order = torch.argsort(center_lum)
        sorted_centers = centers[center_order]
        if sorted_centers.shape[0] < k:
            sorted_centers = torch.cat(
                [
                    sorted_centers,
                    palette_t[sorted_centers.shape[0] :],
                ],
                dim=0,
            )

        # 全图像素归属到最近的中心，再按原图亮度缩放，保留光影明暗
        assign_full = _kmeans_assign(pixels, sorted_centers)
        new_colors = palette_t[assign_full.clamp(0, k - 1)]  # [N,3]
        orig_lum = 0.2126 * pixels[:, 0] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 2]
        pal_lum = 0.2126 * new_colors[:, 0] + 0.7152 * new_colors[:, 1] + 0.0722 * new_colors[:, 2]
        scale = (orig_lum / (pal_lum + 1e-8)).unsqueeze(1)
        new_colors = (new_colors * scale).clamp(0.0, 1.0)
        out.append(new_colors.reshape(H, W, 3))
    return torch.stack(out, dim=0)


class PaletteRecolor:
    """使用预设色卡对图像重新着色。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "palette": (
                    "STRING",
                    {
                        "default": "e8c547-30323d-3f414f-4d5061-5c80bc-cdd1c4",
                        "multiline": False,
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "recolor"
    CATEGORY = "image/postprocessing"

    def recolor(self, image: torch.Tensor, palette: str) -> tuple[torch.Tensor]:
        colors = parse_palette(palette)
        if not colors:
            return (image,)
        out = recolor_image(image, colors)
        return (out,)


# 可选：单独解析色卡并输出为列表的节点（便于预览或给其他节点用）
class ParsePalette:
    """仅解析色卡字符串，输出为可预览的色条图像（1xN 像素）。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "palette": (
                    "STRING",
                    {
                        "default": "https://coolors.co/e8c547-30323d-3f414f-4d5061-5c80bc-cdd1c4",
                        "multiline": False,
                    },
                ),
                "height": ("INT", {"default": 64, "min": 8, "max": 512}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("palette_preview",)
    FUNCTION = "parse"
    CATEGORY = "image/postprocessing"

    def parse(self, palette: str, height: int) -> tuple[torch.Tensor]:
        colors = parse_palette(palette)
        if not colors:
            # 返回 1x1 黑图
            out = torch.zeros(1, height, 1, 3)
            return (out,)
        device = torch.device("cpu")
        k = len(colors)
        w = max(1, k * 32)  # 每色块约 32 像素宽
        arr = torch.zeros(1, height, w, 3, device=device)
        for i, (r, g, b) in enumerate(colors):
            x0 = (i * w) // k
            x1 = ((i + 1) * w) // k
            arr[:, :, x0:x1, 0] = r
            arr[:, :, x0:x1, 1] = g
            arr[:, :, x0:x1, 2] = b
        return (arr,)


NODE_CLASS_MAPPINGS = {
    "PaletteRecolor": PaletteRecolor,
    "ParsePalette": ParsePalette,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PaletteRecolor": "Palette Recolor (色卡重着色)",
    "ParsePalette": "Parse Palette (解析色卡预览)",
}
