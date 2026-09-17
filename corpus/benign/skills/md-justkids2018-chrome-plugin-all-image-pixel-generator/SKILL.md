---
name: image-pixel-generator
description: 生成图片并提取指定位置的像素数据信息
---

# 图像生成与像素数据提取器

生成图片并提取图像中指定位置的像素数据（RGB、RGBA值）。

## 功能特性

1. **生成图片** - 纯色、渐变、测试图案
2. **提取像素数据** - RGB/RGBA值、十六进制颜色
3. **区域分析** - 提取指定区域的像素矩阵

## 使用方法

当用户请求时，我会：
1. 询问图片尺寸和类型
2. 生成HTML Canvas页面
3. 绘制所需图像
4. 提取并显示像素数据

## 示例代码

```html
<!DOCTYPE html>
<html>
<head>
    <title>像素提取器</title>
</head>
<body>
    <canvas id="canvas" width="400" height="300"></canvas>
    <div id="output"></div>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');

        // 绘制图片
        ctx.fillStyle = '#FF5733';
        ctx.fillRect(0, 0, 400, 300);

        // 获取像素
        function getPixel(x, y) {
            const data = ctx.getImageData(x, y, 1, 1).data;
            return {
                r: data[0],
                g: data[1],
                b: data[2],
                a: data[3],
                hex: '#' + ((1 << 24) + (data[0] << 16) + (data[1] << 8) + data[2]).toString(16).slice(1)
            };
        }

        const pixel = getPixel(100, 100);
        document.getElementById('output').innerHTML = `
            <p>位置 (100,100): RGB(${pixel.r}, ${pixel.g}, ${pixel.b})</p>
            <p>十六进制: ${pixel.hex}</p>
        `;
    </script>
</body>
</html>
```

## 输出格式

单个像素：
```json
{
  "position": {"x": 100, "y": 100},
  "rgb": {"r": 255, "g": 87, "b": 51},
  "hex": "#FF5733"
}
```

区域像素矩阵：
```json
{
  "region": {"x": 0, "y": 0, "width": 3, "height": 3},
  "pixels": [[...], [...], [...]]
}
```
