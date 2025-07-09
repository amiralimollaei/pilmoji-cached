from __future__ import annotations

import asyncio
import math

import aiohttp

import PIL
from PIL import Image, ImageDraw, ImageFont

from typing import Dict, Optional, SupportsInt, TYPE_CHECKING, Tuple, Type, TypeVar, Union

from .helpers import NodeType, getsize, to_nodes, paste_image_async
from .source import BaseSource, HTTPBasedSource, Twemoji, CachedHTTPBasedSource

if TYPE_CHECKING:
    from io import BytesIO
    
    FontT = Union[ImageFont.ImageFont, ImageFont.FreeTypeFont, ImageFont.TransposedFont]
    ColorT = Union[int, Tuple[int, int, int], Tuple[int, int, int, int], str]


P = TypeVar('P', bound='PilmojiMain')

__all__ = (
    'PilmojiMain',
    'Pilmoji',
    'PilmojiDrawer'
)


class PilmojiMain:
    """The main emoji rendering interface.

    .. note::
        This should be used in a context manager.

    Parameters
    ----------
    source: Union[:class:`~.BaseSource`, Type[:class:`~.BaseSource`]]
        The emoji image source to use.
        This defaults to :class:`~.TwitterEmojiSource`.
    cache: bool
        Whether or not to cache emojis given from source.
        Enabling this is recommended and by default.
    render_discord_emoji: bool
        Whether or not to render Discord emoji. Defaults to `True`
    emoji_scale_factor: float
        The default rescaling factor for emojis. Defaults to `1`
    emoji_position_offset: Tuple[int, int]
        A 2-tuple representing the x and y offset for emojis when rendering,
        respectively. Defaults to `(0, 0)`
    """

    def __init__(
        self,
        *,
        source: Union[BaseSource, Type[BaseSource]] = Twemoji,
        cache: bool = True,
        render_discord_emoji: bool = True,
        emoji_scale_factor: float = 1.0,
        emoji_position_offset: Tuple[int, int] = (0, 0)
    ) -> None:
        if isinstance(source, type):
            if not issubclass(source, BaseSource):
                raise TypeError(f'source must inherit from BaseSource, not {source}.')

            source = source()

        elif not isinstance(source, BaseSource):
            raise TypeError(f'source must inherit from BaseSource, not {source.__class__}.')

        self.source: BaseSource = source
        
        self._session = aiohttp.ClientSession()

        self._cache: bool = cache
        self._closed: bool = False
        self._new_draw: bool = False

        self._render_discord_emoji: bool = render_discord_emoji
        self._default_emoji_scale_factor: float = emoji_scale_factor
        self._default_emoji_position_offset: Tuple[int, int] = emoji_position_offset

        self._emoji_cache: Dict[str, BytesIO] = {}
        self._discord_emoji_cache: Dict[int, BytesIO] = {}

    async def close(self) -> None:
        """Safely closes this renderer.

        .. note::
            If you are using a context manager, this should not be called.

        Raises
        ------
        ValueError
            The renderer has already been closed.
        """
        if self._closed:
            raise ValueError('Renderer has already been closed.')

        if self._new_draw:
            del self.draw
            self.draw = None

        if hasattr(self.source, "_session"):
            await self.source._session.close()

        if self._cache:
            for stream in self._emoji_cache.values():
                stream.close()

            for stream in self._discord_emoji_cache.values():
                stream.close()

            self._emoji_cache = {}
            self._discord_emoji_cache = {}

        self._closed = True

    async def _get_emoji(self, emoji: str, /) -> Optional[BytesIO]:
        if self._cache and emoji in self._emoji_cache:
            entry = self._emoji_cache[emoji]
            entry.seek(0)
            return entry

        stream = await self.source.get_emoji(emoji)
        if stream:
            if self._cache:
                self._emoji_cache[emoji] = stream

            stream.seek(0)
            return stream

    async def _get_discord_emoji(self, id: SupportsInt | str, /) -> Optional[BytesIO]:
        id = int(id)

        if self._cache and id in self._discord_emoji_cache:
            entry = self._discord_emoji_cache[id]
            entry.seek(0)
            return entry

        stream = await self.source.get_discord_emoji(id)
        if stream:
            if self._cache:
                self._discord_emoji_cache[id] = stream

            stream.seek(0)
            return stream

    async def __aenter__(self: P) -> P:
        # if the source is an HTTPBasedSource and is not wrapped in a CachedHTTPBasedSource,
        # we wrap it in one to enable caching.
        # this is to ensure that the source is always cached if it is an HTTPBasedSource
        self._session = await self._session.__aenter__()
        if isinstance(self.source, HTTPBasedSource):
            self.source._session = self._session
            if not isinstance(self.source, CachedHTTPBasedSource):
                self.source = CachedHTTPBasedSource(self.source)
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f'<Pilmoji source={self.source} cache={self._cache}>'


class PilmojiDrawer:
    def __init__(self, main: PilmojiMain, image: Image.Image, draw: Optional[ImageDraw.ImageDraw]) -> None:
        self._main = main

        self.image = image
        self.draw = draw

        self._create_draw()

    def _create_draw(self) -> None:
        if self.draw is None:
            self._new_draw = True
            self.draw = ImageDraw.Draw(self.image)

    # this function was removed from pillow somewhere around 11.2
    # this is the same functin that pillow used
    # https://github.com/python-pillow/Pillow/blob/main/LICENSE
    def _multiline_spacing(
        self,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont,
        spacing: float,
        stroke_width: int,
    ) -> float:
        assert self.draw
        return (
            self.draw.textbbox((0, 0), "A", font, stroke_width=stroke_width)[3]
            + stroke_width
            + spacing
        )

    def getsize(
        self,
        text: str,
        font: Optional[FontT] = None,
        *,
        spacing: int = 4,
        emoji_scale_factor: Optional[float] = None
    ) -> Tuple[int, int]:
        """Return the width and height of the text when rendered.
        This method supports multiline text.

        Parameters
        ----------
        text: str
            The text to use.
        font
            The font of the text.
        spacing: int
            The spacing between lines, in pixels.
            Defaults to `4`.
        emoji_scalee_factor: float
            The rescaling factor for emojis.
            Defaults to the factor given in the class constructor, or `1`.
        """
        if emoji_scale_factor is None:
            emoji_scale_factor = self._main._default_emoji_scale_factor

        return getsize(text, font, spacing=spacing, emoji_scale_factor=emoji_scale_factor)

    async def text(
        self,
        xy: Tuple[int, int],
        text: str,
        fill: Optional[ColorT] = None,
        font: Optional[FontT] = None,
        anchor: Optional[str] = None,
        spacing: int = 4,
        node_spacing: int = 0,
        align: str = "left",
        direction: Optional[str] = None,
        features: Optional[str] = None,
        language: Optional[str] = None,
        stroke_width: int = 0,
        stroke_fill: Optional[ColorT] = None,
        embedded_color: bool = False,
        *args,
        emoji_scale_factor: Optional[float] = None,
        emoji_position_offset: Optional[Tuple[int, int]] = None,
        **kwargs
    ) -> None:
        """Draws the string at the given position, with emoji rendering support.
        This method supports multiline text.

        .. note::
            Some parameters have not been implemented yet.

        .. note::
            The signature of this function is a superset of the signature of Pillow's `ImageDraw.text`.

        .. note::
            Not all parameters are listed here.

        Parameters
        ----------
        xy: Tuple[int, int]
            The position to render the text at.
        text: str
            The text to render.
        fill
            The fill color of the text.
        font
            The font to render the text with.
        spacing: int
            How many pixels there should be between lines. Defaults to `4`
        node_spacing: int
            How many pixels there should be between nodes (text/unicode_emojis/custom_emojis). Defaults to `0`
        emoji_scale_factor: float
            The rescaling factor for emojis. This can be used for fine adjustments.
            Defaults to the factor given in the class constructor, or `1`.
        emoji_position_offset: Tuple[int, int]
            The emoji position offset for emojis. This can be used for fine adjustments.
            Defaults to the offset given in the class constructor, or `(0, 0)`.
        """

        assert self.draw

        if emoji_scale_factor is None:
            emoji_scale_factor = self._main._default_emoji_scale_factor

        if emoji_position_offset is None:
            emoji_position_offset = self._main._default_emoji_position_offset

        if font is None:
            font = ImageFont.load_default()

        # first we need to test the anchor
        # because we want to make the exact same positions transformations than the "ImageDraw"."text" function in PIL
        # https://github.com/python-pillow/Pillow/blob/66c244af3233b1cc6cc2c424e9714420aca109ad/src/PIL/ImageDraw.py#L449

        # also we are note using the "ImageDraw"."multiline_text" since when we are cuting the text in nodes
        # a lot of code could be simplify this way
        # https://github.com/python-pillow/Pillow/blob/66c244af3233b1cc6cc2c424e9714420aca109ad/src/PIL/ImageDraw.py#L567

        if anchor is None:
            anchor = "la"
        elif len(anchor) != 2:
            msg = "anchor must be a 2 character string"
            raise ValueError(msg)
        elif anchor[1] in "tb" and "\n" in text:
            msg = "anchor not supported for multiline text"
            raise ValueError(msg)

        # need to be checked here because we are not using the real "ImageDraw"."multiline_text"
        if direction == "ttb" and "\n" in text:
            msg = "ttb direction is unsupported for multiline text"
            raise ValueError(msg)

        def getink(fill):
            assert self.draw
            ink, fill = self.draw._getink(fill)
            if ink is None:
                return fill
            return ink

        x, y = xy
        original_x = x
        nodes = to_nodes(text)
        # get the distance between lines ( will be add to y between each line )
        line_spacing = self._multiline_spacing(font, spacing, stroke_width)

        # I change a part of the logic of text writing because it couldn't work "the same as PIL" if I didn't
        nodes_line_to_print = []
        widths = []
        max_width = 0
        streams = {}
        mode = self.draw.fontmode
        if stroke_width == 0 and embedded_color:
            mode = "RGBA"
        ink = getink(fill)
        # we get the size taken by a " " to be drawn with the given options
        space_text_lenght = self.draw.textlength(" ", font, direction=direction,
                                                 features=features, language=language, embedded_color=embedded_color)

        for node_id, line in enumerate(nodes):
            text_line = ""
            streams[node_id] = {}
            
            async def process_line(line_id, node):
                content = node.content
                stream = None
                if node.type is NodeType.emoji:
                    stream = await self._main._get_emoji(content)

                elif self._main._render_discord_emoji and node.type is NodeType.discord_emoji:
                    stream = await self._main._get_discord_emoji(content)

                if stream:
                    streams[node_id][line_id] = stream
                
                return node, stream
            
            # this will fetch all emojis asynchronously
            streams_processed = await asyncio.gather(*[
                process_line(line_id, node) for line_id, node in enumerate(line)
            ])

            for node, stream in streams_processed:
                if node.type is NodeType.text or not stream:
                    # each text in the same line are concatenate
                    text_line += node.content
                    continue

                width = round(emoji_scale_factor * font.size)
                ox, oy = emoji_position_offset
                size = round(width + ox + (node_spacing * 2))
                # for every emoji we calculate the space needed to display it in the current text
                space_to_had = round(size / space_text_lenght)
                # we had the equivalent space as " " caracter in the line text
                text_line += "".join(" " for x in range(space_to_had))

            # saving each line with the place to display emoji at the right place
            nodes_line_to_print.append(text_line)
            line_width = self.draw.textlength(
                text_line, font, direction=direction, features=features, language=language
            )
            widths.append(line_width)
            max_width = max(max_width, line_width)

        # taking into acount the anchor to place the text in the right place
        if anchor[1] == "m":
            y -= (len(nodes) - 1) * line_spacing / 2.0
        elif anchor[1] == "d":
            y -= (len(nodes) - 1) * line_spacing

        paste_tasks = []
        for node_id, line in enumerate(nodes):
            # restore the original x wanted for each line
            x = original_x
            # some transformations should not be applied to y
            line_y = y
            width_difference = max_width - widths[node_id]

            # first align left by anchor
            if anchor[0] == "m":
                x -= width_difference / 2.0
            elif anchor[0] == "r":
                x -= width_difference

            # then align by align parameter
            if align == "left":
                pass
            elif align == "center":
                x += width_difference / 2.0
            elif align == "right":
                x += width_difference
            else:
                msg = 'align must be "left", "center" or "right"'
                raise ValueError(msg)

            # if this line hase text to display then we draw it all at once ( one time only per line )
            if len(nodes_line_to_print[node_id]) > 0:
                self.draw.text(
                    (x, line_y),
                    nodes_line_to_print[node_id],
                    fill=fill,
                    font=font,
                    anchor=anchor,
                    spacing=spacing,
                    align=align,
                    direction=direction,
                    features=features,
                    language=language,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_fill,
                    embedded_color=embedded_color,
                    *args,
                    **kwargs
                )

            coord = []
            start = []
            for i in range(2):
                coord.append(int((x, y)[i]))
                start.append(math.modf((x, y)[i])[0])

            # respecting the way parameters are used in PIL to find the good x and y
            if ink is not None:
                stroke_ink = None
                if stroke_width:
                    stroke_ink = getink(stroke_fill) if stroke_fill is not None else ink

                if stroke_ink is not None:
                    ink = stroke_ink
                    stroke_width = 0
                try:
                    _, offset = font.getmask2(
                        nodes_line_to_print[node_id],
                        mode,
                        direction=direction,
                        features=features,
                        language=language,
                        stroke_width=stroke_width,
                        anchor=anchor,
                        ink=ink,
                        start=start,
                        *args,
                        **kwargs,
                    )
                    coord = coord[0] + offset[0], coord[1] + offset[1]
                except AttributeError:
                    pass
                x, line_y = coord
            
            for line_id, node in enumerate(line):
                content = node.content

                # if node is text then we decale our x
                # but since the text line as already be drawn we do not need to draw text here anymore
                if node.type is NodeType.text or line_id not in streams[node_id]:
                    if tuple(int(part) for part in PIL.__version__.split(".")) >= (9, 2, 0):
                        width = int(font.getlength(content, direction=direction, features=features, language=language))
                    else:
                        width, _ = font.getsize(content)
                    x += node_spacing + width
                    continue

                if line_id in streams[node_id]:
                    with Image.open(streams[node_id][line_id]).convert('RGBA') as asset:
                        width = round(emoji_scale_factor * font.size)
                        size = width, round(math.ceil(asset.height / asset.width * width))
                        asset = asset.resize(size, Image.Resampling.LANCZOS)
                        ox, oy = emoji_position_offset

                        self.image.paste(asset, (round(x + ox), round(line_y + oy)), asset)

                x += node_spacing + width
            y += line_spacing


class Pilmoji(PilmojiMain):
    def new_draw(self, image: Image.Image, draw: Optional[ImageDraw.ImageDraw] = None) -> PilmojiDrawer:
        return PilmojiDrawer(self, image, draw)
