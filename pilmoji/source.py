from abc import ABC, abstractmethod
from io import BytesIO

from urllib.parse import quote_plus

import os
import hashlib
import asyncio
import logging

from typing import Any, ClassVar, Dict, Optional

import aiofiles
import aiohttp


__all__ = (
    'BaseSource',
    'HTTPBasedSource',
    'CachedHTTPBasedSource',
    'DiscordEmojiSourceMixin',
    'EmojiCDNSource',
    'TwitterEmojiSource',
    'AppleEmojiSource',
    'GoogleEmojiSource',
    'MicrosoftEmojiSource',
    'FacebookEmojiSource',
    'MessengerEmojiSource',
    'EmojidexEmojiSource',
    'JoyPixelsEmojiSource',
    'SamsungEmojiSource',
    'WhatsAppEmojiSource',
    'MozillaEmojiSource',
    'OpenmojiEmojiSource',
    'TwemojiEmojiSource',
    'FacebookMessengerEmojiSource',
    'Twemoji',
    'Openmoji',
)

CACHE_DIR = os.path.abspath(".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class BaseSource(ABC):
    """The base class for an emoji image source."""

    @abstractmethod
    async def get_emoji(self, emoji: str, /) -> Optional[BytesIO]:
        """Retrieves a :class:`io.BytesIO` stream for the image of the given emoji.

        Parameters
        ----------
        emoji: str
            The emoji to retrieve.

        Returns
        -------
        :class:`io.BytesIO`
            A bytes stream of the emoji.
        None
            An image for the emoji could not be found.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_discord_emoji(self, id: int, /) -> Optional[BytesIO]:
        """Retrieves a :class:`io.BytesIO` stream for the image of the given Discord emoji.

        Parameters
        ----------
        id: int
            The snowflake ID of the Discord emoji.

        Returns
        -------
        :class:`io.BytesIO`
            A bytes stream of the emoji.
        None
            An image for the emoji could not be found.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}>'


class HTTPBasedSource(BaseSource):
    """Represents an HTTP-based source."""

    REQUEST_KWARGS: ClassVar[Dict[str, Any]] = {
        'headers': {'User-Agent': 'Mozilla/5.0'}
    }

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def request(self, url: str) -> BytesIO | None:
        """Makes a GET request to the given URL.

        Parameters
        ----------
        url: str
            The URL to request from.

        Returns
        -------
        bytes

        Raises
        ------
        Union[:class:`requests.HTTPError`, :class:`urllib.error.HTTPError`]
            There was an error requesting from the URL.
        """

        assert self._session is not None, "Session must be initialized before making requests"

        response = await self._session.get(url, timeout=aiohttp.ClientTimeout(total=10))
        if response.ok:
            return BytesIO(await response.content.read())
        else:
            raise aiohttp.ClientError(f'Failed to fetch emoji from {url}, status code: {response.status}')

    @abstractmethod
    async def get_emoji(self, emoji: str, /) -> Optional[BytesIO]:
        raise NotImplementedError

    @abstractmethod
    async def get_discord_emoji(self, id: int, /) -> Optional[BytesIO]:
        raise NotImplementedError


class DiscordEmojiSourceMixin(HTTPBasedSource):
    """A mixin that adds Discord emoji functionality to another source."""

    BASE_DISCORD_EMOJI_URL: ClassVar[str] = 'https://cdn.discordapp.com/emojis/'

    @abstractmethod
    async def get_emoji(self, emoji: str, /) -> Optional[BytesIO]:
        raise NotImplementedError

    async def get_discord_emoji(self, id: int, /) -> Optional[BytesIO]:
        url = self.BASE_DISCORD_EMOJI_URL + str(id) + '.png'

        try:
            return await self.request(url)
        except aiohttp.ClientError:
            logging.critical(f'Failed to fetch Discord emoji with ID {id} from {url}')
            raise


class EmojiCDNSource(DiscordEmojiSourceMixin):
    """A base source that fetches emojis from https://emojicdn.elk.sh/."""

    BASE_EMOJI_CDN_URL: ClassVar[str] = 'https://emojicdn.elk.sh/'
    STYLE: ClassVar[str] = None

    async def get_emoji(self, emoji: str, /) -> Optional[BytesIO]:
        if self.STYLE is None:
            raise TypeError('STYLE class variable unfilled.')

        url = self.BASE_EMOJI_CDN_URL + quote_plus(emoji) + '?style=' + quote_plus(self.STYLE)
        try:
            return await self.request(url)
        except aiohttp.ClientError:
            logging.critical(f'Failed to fetch Discord emoji with ID {id} from {url}')
            raise


class TwitterEmojiSource(EmojiCDNSource):
    """A source that uses Twitter-style emojis. These are also the ones used in Discord."""
    STYLE = 'twitter'


class AppleEmojiSource(EmojiCDNSource):
    """A source that uses Apple emojis."""
    STYLE = 'apple'


class GoogleEmojiSource(EmojiCDNSource):
    """A source that uses Google emojis."""
    STYLE = 'google'


class MicrosoftEmojiSource(EmojiCDNSource):
    """A source that uses Microsoft emojis."""
    STYLE = 'microsoft'


class SamsungEmojiSource(EmojiCDNSource):
    """A source that uses Samsung emojis."""
    STYLE = 'samsung'


class WhatsAppEmojiSource(EmojiCDNSource):
    """A source that uses WhatsApp emojis."""
    STYLE = 'whatsapp'


class FacebookEmojiSource(EmojiCDNSource):
    """A source that uses Facebook emojis."""
    STYLE = 'facebook'


class MessengerEmojiSource(EmojiCDNSource):
    """A source that uses Facebook Messenger's emojis."""
    STYLE = 'messenger'


class JoyPixelsEmojiSource(EmojiCDNSource):
    """A source that uses JoyPixels' emojis."""
    STYLE = 'joypixels'


class OpenmojiEmojiSource(EmojiCDNSource):
    """A source that uses Openmoji emojis."""
    STYLE = 'openmoji'


class EmojidexEmojiSource(EmojiCDNSource):
    """A source that uses Emojidex emojis."""
    STYLE = 'emojidex'


class MozillaEmojiSource(EmojiCDNSource):
    """A source that uses Mozilla's emojis."""
    STYLE = 'mozilla'


class CachedHTTPBasedSource(BaseSource):
    """A wrapper for any HTTPBasedSource that caches emoji images in CACHE_DIR."""

    def __init__(self, source: HTTPBasedSource) -> None:
        if not isinstance(source, HTTPBasedSource):
            raise TypeError('source must be an instance of HTTPBasedSource')
        self._source = source

    @property
    def _session(self):
        return self._source._session
    
    def _emoji_cache_path(self, emoji: str) -> str:
        key = hashlib.sha256(emoji.encode('utf-8')).hexdigest()
        return os.path.join(CACHE_DIR, f'{self._source.__class__.__name__}_{key}.png')

    def _discord_cache_path(self, id: int) -> str:
        return os.path.join(CACHE_DIR, f'discord_{id}.png')

    async def get_emoji(self, emoji: str, /) -> Optional[BytesIO]:
        path = self._emoji_cache_path(emoji)
        if os.path.exists(path):
            async with aiofiles.open(path, 'rb') as f:
                return BytesIO(await f.read())
        data = await self._source.get_emoji(emoji)
        if data is not None:
            async with aiofiles.open(path, 'wb') as f:
                await f.write(data.read())
            data.seek(0)
            return data

    async def get_discord_emoji(self, id: int, /) -> Optional[BytesIO]:
        path = self._discord_cache_path(id)
        if os.path.exists(path):
            async with aiofiles.open(path, 'rb') as f:
                return BytesIO(await f.read())
        data = await self._source.get_discord_emoji(id)
        if data is not None:
            async with aiofiles.open(path, 'wb') as f:
                await f.write(data.read())
            data.seek(0)
            return data


# Aliases
Openmoji = OpenmojiEmojiSource
FacebookMessengerEmojiSource = MessengerEmojiSource
TwemojiEmojiSource = Twemoji = TwitterEmojiSource
