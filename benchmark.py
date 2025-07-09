import asyncio
import time
import tqdm
from pilmoji import Pilmoji
from PIL import Image, ImageFont

my_string = '''
Hello, world! 👋 Here are some emojis: 🎨 🌊 😎
I also support Discord emoji: <:rooThink:596576798351949847>
'''.strip()
num_images = 1

async def main():
    font = ImageFont.truetype('arial.ttf', 48)
    async with Pilmoji(emoji_position_offset=(5, -5)) as p:
        for i in tqdm.tqdm(range(num_images)):
            with Image.new('RGB', (550*2, 80*2), (255, 255, 255)) as image:
                imagedraw = p.new_draw(image)
                await imagedraw.text((30, 30), my_string, (0, 0, 0), font)
                image.show()

if __name__ == "__main__":
    st = time.time()
    asyncio.run(main())
    et = time.time()

    time_taken = et - st
    time_per_image = time_taken/num_images

    print(f"{time_taken=}, {time_per_image=}")
