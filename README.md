# Pilmoji

Pilmoji is an emoji renderer for [Pillow](https://github.com/python-pillow/Pillow/),
Python's imaging library.

Pilmoji comes equipped with support for both unicode emojis and Discord emojis.

## Pilmoji-cached

Pilmoji-cached is a fork of Pilmoji that adds persistant caching to emojis and improves
overall performance by making some operations asynchronous

## Features

- Discord emoji support
- Multi-line rendering support
- Emoji position and/or size adjusting
- Many built-in emoji sources
- Optional in-memory caching
- Always-On persistant caching

## Installation and Requirements

You must have Python 3.10 or higher in order to install Pilmoji.

Installation can be done with `pip`:

```shell
pip install -U git+https://github.com/amiralimollaei/pilmoji-cached
```

## Usage

```py
from pilmoji import Pilmoji
from PIL import Image, ImageFont


my_string = '''
Hello, world! 👋 Here are some emojis: 🎨 🌊 😎
I also support Discord emoji: <:rooThink:596576798351949847>
'''

with Image.new('RGB', (550, 80), (255, 255, 255)) as image:
    font = ImageFont.truetype('arial.ttf', 24)

   async with Pilmoji() as pilmoji:
        await pilmoji.new_draw(image).text((10, 10), my_string.strip(), (0, 0, 0), font)

    image.show()
```

## Switching emoji sources

As seen from the example, Pilmoji defaults to the `Twemoji` emoji source.

If you prefer emojis from a different source, for example Microsoft, simply
set the `source` kwarg in the constructor to a source found in the
`pilmoji.source` module:

```py
from pilmoji.source import MicrosoftEmojiSource

async with Pilmoji(source=MicrosoftEmojiSource) as pilmoji:
    ...
```

It is also possible to create your own emoji sources via subclass.

## Fine adjustments

If an emoji looks too small or too big, or out of place, you can make fine adjustments
with the `emoji_scale_factor` and `emoji_position_offset` kwargs:

```py
pilmoji.new_draw(image).text((10, 10), my_string.strip(), (0, 0, 0), font,
             emoji_scale_factor=1.15, emoji_position_offset=(0, -2))
```

## Contributing

Contributions are welcome. Make sure to follow [PEP-8](https://www.python.org/dev/peps/pep-0008/)
styling guidelines.
