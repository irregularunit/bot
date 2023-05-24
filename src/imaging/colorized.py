# -*- coding: utf-8 -*-

"""
Serenity License (Attribution-NonCommercial-ShareAlike 4.0 International)

You are free to:

  - Share: copy and redistribute the material in any medium or format.
  - Adapt: remix, transform, and build upon the material.

The licensor cannot revoke these freedoms as long as you follow the license
terms.

Under the following terms:

  - Attribution: You must give appropriate credit, provide a link to the
    license, and indicate if changes were made. You may do so in any reasonable
    manner, but not in any way that suggests the licensor endorses you or your
    use.
  
  - Non-Commercial: You may not use the material for commercial purposes.
  
  - Share Alike: If you remix, transform, or build upon the material, you must
    distribute your contributions under the same license as the original.
  
  - No Additional Restrictions: You may not apply legal terms or technological
    measures that legally restrict others from doing anything the license
    permits.

This is a human-readable summary of the Legal Code. The full license is available
at https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode
"""

from __future__ import annotations

import asyncio
import io
import struct
import zlib

from .abc import SavableByteStream

__all__: tuple[str, ...] = ('RGB', 'ColorRepresentation')


class RGB:
    """Represents an RGB color."""

    __slots__: tuple[str, ...] = ('_r', '_g', '_b')

    _r: int
    _g: int
    _b: int

    def __init__(self, r: int, g: int, b: int) -> None:
        self._r = r
        self._g = g
        self._b = b

    def __post_init__(self) -> None:
        if not all(0 <= c <= 255 for c in (self.rgb)):
            raise ValueError('RGB values must be between 0 and 255.')

    @property
    def r(self) -> int:
        return self._r

    @property
    def g(self) -> int:
        return self._g

    @property
    def b(self) -> int:
        return self._b

    @property
    def rgb(self) -> tuple[int, int, int]:
        return self._r, self._g, self._b

    @property
    def hsl(self) -> tuple[float, float, float]:
        """Convert the color to HSL format."""

        r, g, b = self.rgb
        r /= 255
        g /= 255
        b /= 255

        cmax = max(r, g, b)
        cmin = min(r, g, b)
        delta = cmax - cmin

        if delta == 0:
            hue = 0
        elif cmax == r:
            hue = 60 * (((g - b) / delta) % 6)
        elif cmax == g:
            hue = 60 * (((b - r) / delta) + 2)
        else:  # cmax == b
            hue = 60 * (((r - g) / delta) + 4)

        lightness = (cmax + cmin) * 0.5

        saturation = 0 if delta == 0 else delta / (1 - abs(2 * lightness - 1))
        return hue, saturation, lightness

    def __repr__(self) -> str:
        return f'RGB(r={self._r}, g={self._g}, b={self._b})'


class ColorRepresentation(SavableByteStream):
    """Represents a colorized image.

    This class is super barebones and only supports PNGs with 8-bit color depth and 2 color channels.
    On the other hand, it's very fast and memory-efficient. It's also not very flexible, but that's
    not the point of this class.

    Attributes
    ----------
    rgb: `RGB`
        The color to use for the image.
    width: `int`
        The width of the image, in pixels.
    height: `int`
        The height of the image, in pixels.
    """

    __slots__: tuple[str, ...] = ('_rgb', '_width', '_height')

    _rgb: RGB
    _width: int
    _height: int
    _instructions: list[bytes]

    def __init__(self, width: int, height: int, rgb: RGB) -> None:
        self._rgb = rgb
        self._width = width
        self._height = height
        self._instructions = [
            b'\x89PNG\r\n\x1a\n',
            self._generate_header_chunk(width, height),
            self._generate_data_chunk(width, height),
            self._generate_end_chunk(),
        ]

    @property
    def colour(self) -> RGB:
        return self._rgb

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._rgb})'

    @staticmethod
    def _generate_chunk(chunk_type: bytes, data: bytes) -> bytes:
        """Generate a PNG chunk, including the 4-byte length prefix and the 4-byte chunk type."""
        chunk_header = struct.pack('!I', len(data))
        return chunk_header + chunk_type + data + struct.pack('!I', zlib.crc32(chunk_type + data))

    def _generate_header_chunk(self, width: int, height: int) -> bytes:
        """Generate the IHDR chunk, which contains information about the image."""

        # IHDR data contains:
        # - width:              4 bytes
        # - height:             4 bytes
        # - bit depth:          1 byte
        # - color type:         1 byte
        # - compression method: 1 byte
        # - filter method:      1 byte
        # - interlace method:   1 byte
        data = struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0)

        return self._generate_chunk(b'IHDR', data)

    def _generate_data_chunk(self, width: int, height: int) -> bytes:
        """Generate the IDAT chunk, which contains the image data."""

        # The filter byte is set to 0, indicating "None".
        # See: http://www.libpng.org/pub/png/spec/1.2/PNG-Compression.html
        raw_data = b''.join(b'\x00' + bytes(self.colour.rgb) * width for _ in range(height))

        compressed_data = zlib.compress(raw_data)
        return self._generate_chunk(b'IDAT', compressed_data)

    def _generate_end_chunk(self) -> bytes:
        """Generate the IEND chunk, which indicates that the image is complete."""
        return self._generate_chunk(b'IEND', b'')

    async def buffer(self) -> io.BytesIO:
        return await asyncio.to_thread(self.raw)

    def raw(self) -> io.BytesIO:
        buffer = io.BytesIO()

        for instruction in self._instructions:
            buffer.write(instruction)

        buffer.seek(0)
        return buffer
