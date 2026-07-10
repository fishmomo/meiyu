"""
该代码主要用于将已有静态图片组合成连续的GIF动图
"""

from PIL import Image
import os
from project_paths import animation_path

def create_gif(image_folder, output_path, duration=500):
    """
    从指定文件夹中读取图片并生成 GIF 动图

    参数:
    - image_folder: 存放图片的文件夹路径
    - output_path: 生成的 GIF 输出路径
    - duration: 每帧显示时间（毫秒）
    """
    # 读取所有图片文件，按文件名排序
    images = [Image.open(os.path.join(image_folder, f))
              for f in sorted(os.listdir(image_folder)) if f.endswith(('.png', '.jpg', '.jpeg', '.PNG'))]
    
    if not images:
        print("未找到图片。")
        return

    # 保存为 GIF
    images[0].save(output_path,
                   save_all=True,
                   append_images=images[1:],
                   duration=duration,
                   loop=0)
    print(f"GIF 已保存至：{output_path}")

# 使用示例
if __name__ == '__main__':

    create_gif(
        image_folder=r'H:\YeWu\WRJ_obs\batch_rhi_output_300dpi\70',
        output_path=animation_path("examples", filename="output.gif"),
        duration=800,
    )
