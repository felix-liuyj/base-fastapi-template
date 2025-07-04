from enum import Enum

__all__ = (
    'SupportImageMIMEType',
    'SupportDataMIMEType',
)


class SupportDataMIMEType(Enum):
    TEXT_PLAIN = 'text/plain'
    TEXT_HTML = 'text/html'
    APPLICATION_JSON = 'application/json'

    @classmethod
    def check_value_exists(cls, value: str) -> 'SupportImageMIMEType':
        for member in cls:
            if member.value == value:
                return cls(value)


class SupportImageMIMEType(Enum):
    IMAGE_PNG = 'image/png'
    IMAGE_JPG = 'image/jpeg'
    IMAGE_JPEG = 'image/jpeg'
    IMAGE_SVG = 'image/svg+xml'

    @classmethod
    def check_value_exists(cls, value: str) -> 'SupportImageMIMEType':
        for member in cls:
            if member.value == value:
                return cls(value)
