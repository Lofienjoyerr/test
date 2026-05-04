import io
from pathlib import Path
from typing import Optional, Union, Literal, Generator

from PIL import Image, ImageOps, ImageFilter
from django.core.files.base import ContentFile, File
from wand.color import Color
from wand.image import Image as WandImage


def get_filename_extension(*, file_name:str) -> str:
    return Path(file_name).suffix[1:].lower()


class ImageExtension:
    JPEG = 'jpeg'
    WEBP = 'webp'


class ImageProcessor:
    """
    Интерфейс для взаимодействия с изображениями.

    Также может обрабатывать pdf.
    """

    DEFAULT_QUALITY_BY_BIGGEST_SIDE = {
        500: 90,
        1000: 80,
        2000: 70,
    }
    """Отсортированный маппинг дефолтных значений качества изображения и наибольшей стороны"""

    def __init__(self, source: Union[str, Path, io.BytesIO, File]) -> None:
        self._source = source

        extension = self._get_extension(source)

        if extension != 'pdf':
            with Image.open(source) as img:
                self._format = img.format
                img = ImageOps.exif_transpose(img)
                self._img = img
                self._img.load()

    # Конвертации формата

    def to_jpeg(self) -> 'ImageProcessor':
        """Конвертирует в JPEG. Прозрачный фон заменяется на белый."""
        if self._img.mode == 'P':
            self._img = self._img.convert('RGBA')

        if self._img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', self._img.size, (255, 255, 255))
            background.paste(self._img, mask=self._img.split()[-1])
            self._img = background
        else:
            self._img = self._img.convert('RGB')

        self._format = 'JPEG'

        return self

    def to_webp(self) -> 'ImageProcessor':
        """Конвертирует в WebP. Сохраняет прозрачность для RGBA."""
        if self._img.mode in ('LA', 'P'):
            self._img = self._img.convert('RGBA')
        elif self._img.mode not in ('RGB', 'RGBA'):
            self._img = self._img.convert('RGB')

        self._format = 'WEBP'

        return self

    # Трансформации

    def resize(
        self,
        width: int,
        height: int,
        resample: Image.Resampling = Image.Resampling.LANCZOS,
    ) -> 'ImageProcessor':
        """Изменяет размер до точных значений без сохранения пропорций."""
        self._img = self._img.resize((width, height), resample=resample)

        return self

    def thumbnail(
        self,
        max_size: tuple[int, int],
        resample: Image.Resampling = Image.Resampling.LANCZOS,
    ) -> 'ImageProcessor':
        """Уменьшает изображение, сохраняя пропорции. Не увеличивает."""
        self._img.thumbnail(max_size, resample=resample)

        return self

    def crop(self, box: tuple[int, int, int, int]) -> 'ImageProcessor':
        """Обрезает изображение по box=(left, upper, right, lower)."""
        self._img = self._img.crop(box)

        return self

    def watermark(
        self,
        watermark_source: Union[str, Path, io.BytesIO, File],
        *,
        position: Optional[tuple[int, int]] = None,
        opacity: float = 1.0,
    ) -> 'ImageProcessor':
        """
        Наложение watermark на изображение.

        :param watermark_source: Источник watermark (путь/файл).
        :param position: Позиция установки watermark (x, y).
        :param opacity: Непрозрачность 0.0 - 1.0.
        """
        with Image.open(watermark_source) as tmp:
            watermark = tmp.copy()

        if position is None:
            position = (0, 0)

        if opacity < 1.0:
            alpha = watermark.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            watermark.putalpha(alpha)

        self._img.paste(watermark, position, watermark)

        return self

    def filter(self, filter_type: Literal['blur', 'contour', 'sharpen', 'edge']) -> 'ImageProcessor':
        """
        Применяет фильтр к изображению.

        :param filter_type: blur — размытие, contour — контур, sharpen — резкость, edge — края.
        """
        filters = {
            'blur': ImageFilter.BLUR,
            'contour': ImageFilter.CONTOUR,
            'sharpen': ImageFilter.SHARPEN,
            'edge': ImageFilter.EDGE_ENHANCE,
        }
        self._img = self._img.filter(filters[filter_type])
        return self

    def rotate(self, angle: float = 90) -> 'ImageProcessor':
        """
        Поворачивает изображение против часовой стрелки.

        :param angle: Угол поворота в градусах.
        """
        self._img = self._img.rotate(angle)
        return self

    # Вывод

    def to_content_file(self, *, quality: Optional[int] = None) -> 'ContentFile':
        """Возвращает ContentFile с изображением в текущем формате."""
        if quality is None:
            quality = self._get_quality()

        extra_kwargs = {}
        if self._format == 'JPEG':
            extra_kwargs['optimize'] = True

        buf = io.BytesIO()
        self._img.save(buf, format=self._format, quality=quality, **extra_kwargs)
        buf.seek(0)

        return ContentFile(buf.read())

    def save(self, path: Union[str, Path], *, quality: Optional[int] = None) -> None:
        """Сохраняет изображение на диск в текущем формате."""
        if quality is None:
            quality = self._get_quality()

        extra_kwargs = {}
        if self._format == 'JPEG':
            extra_kwargs['optimize'] = True

        self._img.save(path, format=self._format, quality=quality, **extra_kwargs)

    def images_from_pdf(
        self,
        *,
        file_format: str = ImageExtension.JPEG,
        resolution: int = 150,
        pages_pattern: str = '*',
    ) -> Generator[ContentFile, None, None]:
        kwargs: dict = {'resolution': resolution}
        if isinstance(self._source, (str, Path)):
            kwargs['filename'] = self._source
        else:
            kwargs['file'] = self._source

        images_bytes_list = []

        with WandImage(**kwargs) as pdf:
            pdf.background_color = Color('white')
            pdf.alpha_channel = 'remove'

            if pages_pattern == '*':
                for page in pdf.sequence:
                    blob = WandImage(page).make_blob(file_format)
                    images_bytes_list.append(blob)
            else:
                pages_numbers = self._parse_pages_pattern(pages_pattern)
                for page_number in pages_numbers:
                    blob = WandImage(pdf.sequence[page_number]).make_blob(file_format)
                    images_bytes_list.append(blob)

        for image_bytes_list in images_bytes_list:
            yield ContentFile(image_bytes_list)

    # Утилиты

    def _get_quality(self):
        """Получить дефолтное значение качества изображения по наибольшей стороне."""
        biggest_side = max(self._img.size)

        return next(
            new_quality
            for max_side, new_quality in self.DEFAULT_QUALITY_BY_BIGGEST_SIDE.items()
            if biggest_side <= max_side
        )

    @staticmethod
    def _get_extension(source: Union[str, Path, io.BytesIO, File]) -> str:
        if isinstance(source, (io.BytesIO, File)):
            source = getattr(source, 'name', '')
        return get_filename_extension(file_name=source)

    @staticmethod
    def _parse_pages_pattern(pages_pattern: str) -> list[int]:
        pages_numbers = []
        pages_pattern = pages_pattern.replace(' ', '')

        for token in pages_pattern.split(','):
            if '-' in token:
                left_border, right_border = token.split('-')
                for page_index in range(int(left_border), int(right_border) + 1):
                    pages_numbers.append(int(page_index))
            else:
                pages_numbers.append(int(token))

        return pages_numbers


if __name__ == '__main__':
    cfs = ImageProcessor('sample.pdf').images_from_pdf()
    for idx, cf in enumerate(cfs):
        with open(f'zxc_{idx}.jpg', 'wb') as f:
            f.write(cf.read())
