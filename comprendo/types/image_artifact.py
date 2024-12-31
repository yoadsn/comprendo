from io import BytesIO
import base64

from PIL import Image
from attrs import define


@define
class ImageArtifact:
    value: bytes
    format: str
    width: int
    height: int

    @property
    def base64(self) -> str:
        return base64.b64encode(self.value).decode('utf8')

    @property
    def mime_type(self) -> str:
        return f"image/{self.format}"

    def to_bytes(self) -> bytes:
        return self.value

    def to_text(self) -> str:
        return f"<Image ({self.format}), {self.width}x{self.height}, {len(self.value)} bytes>"

    def __str__(self) -> str:
        return self.to_text()

    def __repr__(self) -> str:
        return self.__str__()

    def __bool__(self) -> bool:
        return bool(self.value)

    def __len__(self) -> int:
        return len(self.value)

    @classmethod
    def from_pil_image(cls, pil_image: Image, format: str = "PNG"):
        byte_stream = BytesIO()
        pil_image.save(byte_stream, format=format)
        byte_stream.seek(0)
        return cls(
            byte_stream.getvalue(), format=pil_image.format.lower(), width=pil_image.width, height=pil_image.height
        )
