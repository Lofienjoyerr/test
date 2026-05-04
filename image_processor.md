# ImageProcessor

Универсальный интерфейс для работы с изображениями.

Покрывает следующие сценарии:
1. Необходимо открыть и прочитать файл изображения с диска, изменить его (по необходимости) и подготовить ContentFile
2. Необходимо открыть и прочитать файл изображения с диска, изменить его (по необходимости) и сохранить на диск
3. Необходимо получить по API файл изображения, изменить его (по необходимости) и подготовить ContentFile (который уже можно будет поместить в ImageField)
4. Необходимо получить по API pdf-документ и подготовить генератор ContentFile определённых страниц документа.
5. Необходимо открыть с диска pdf-документ и подготовить генератор ContentFile определённых страниц документа.

Примеры использования
```python
img = serializer.validated_data['img']  # InMemoryUploadedFile[png, jpg, webp...]
(
    ImageProcessor(img)
    .watermark('watermark.png')
    .to_jpeg()
    .save('image.jpg')
)
```

```python
img = serializer.validated_data['img']  # InMemoryUploadedFile[png, jpg, webp...]
content_file = (
     ImageProcessor(img)
     .watermark('watermark.png', position=(450, 350))
     .to_jpeg()
     .to_content_file()
)
```

```python
img = serializer.validated_data['img']  # InMemoryUploadedFile[png, jpg, webp...]
content_file = (
    ImageProcessor(img)
    .watermark('watermark.png', position=(450, 350), opacity=0.4)
    .to_jpeg()
    .to_content_file()
)
```

```python
img = serializer.validated_data['img']  # InMemoryUploadedFile[png, jpg, webp...]
content_file = (
    ImageProcessor(img)
    .to_jpeg()
    .thumbnail((2000, 2000))
    .to_content_file()
)
```

```python
img = serializer.validated_data['img']  # InMemoryUploadedFile[png, jpg, webp...]
(
    ImageProcessor(img)
    .to_jpeg()
    .thumbnail((2000, 2000))
    .save('new_image.jpg')
)
```

```python
img = serializer.validated_data['img']  # InMemoryUploadedFile[png, jpg, webp...]
(
    ImageProcessor(img)
    .to_jpeg()
    .thumbnail((2000, 2000))
    .save('new_image.jpg', quality=75)
)
```

```python
img = serializer.validated_data['pdf_file']  # InMemoryUploadedFile[pdf]
content_files = (
    ImageProcessor(img)
    .images_from_pdf()
)
for content_file in content_files:
    DjangoModelWithFile(file_field_name=content_file).save()
```

```python
img = serializer.validated_data['pdf_file']  # InMemoryUploadedFile[pdf]
content_files = (
    ImageProcessor(img)
    .images_from_pdf(
        file_format='png',
        pages_pattern='1,3,5,7-10,14,18-23',  # Индексация с 1
    )
)
for content_file in content_files:
    DjangoModelWithFile(file_field_name=content_file).save()
```

```python
ImageProcessor('sample.png').to_jpeg().save('image.jpg')
```

```python
ImageProcessor('sample.jpg').to_webp().save('image.webp')
```