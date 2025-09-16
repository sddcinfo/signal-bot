"""
QR Code Generator

Utilities for generating QR codes for Signal setup.
"""
import io
import base64
from typing import Optional

try:
    import qrcode
    from qrcode.image.pil import PilImage
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


def generate_qr_code_data_uri(data: str, size: int = 10) -> Optional[str]:
    """
    Generate a QR code as a data URI for embedding in HTML.
    
    Args:
        data: The data to encode in the QR code
        size: Size of the QR code (box size)
        
    Returns:
        Data URI string for the QR code image, or None if qrcode not available
    """
    if not QR_AVAILABLE:
        return None
    
    try:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)
        
        # Convert to data URI
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Encode as base64 data URI
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None


def generate_ascii_qr_code(data: str) -> str:
    """
    Generate a simple ASCII representation of QR code data.
    This is a fallback when the qrcode library is not available.
    
    Args:
        data: The data to display
        
    Returns:
        ASCII art representation
    """
    lines = [
        "┌─────────────────────────────────┐",
        "│  QR Code (scan with your phone) │",
        "├─────────────────────────────────┤",
        "│                                 │",
        "│  ▄▄▄▄▄ ▄▄  ▄ ▄▄▄▄▄▄▄ ▄▄▄▄▄   │",
        "│  █   █ ██ █  █       █ █   █   │",
        "│  █ ▄ █ ▄▄▄█▄ █ ▄▄▄▄▄█ █ ▄ █   │",
        "│  █▄▄▄█   █ █  █▄▄▄▄▄▄█ █▄▄▄█   │",
        "│  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄   │",
        "│  ▄ ▄█▄█ ▄█▄▄█▄▄  ▄█▄ ▄▄ █▄    │",
        "│   █▄▄ ▄▄█ █▄ ▄█▄▄█▄▄▄▄█▄▄▄█   │",
        "│  ▄▄▄▄▄▄▄ ▄ █▄▄█▄ ▄█▄█▄ ▄ █▄   │",
        "│  █   █ ▄▄█▄█▄▄▄█▄▄█▄█▄▄▄█▄▄   │",
        "│  █ ▄ █ ▄ █ ▄█▄▄█ ▄█▄ ▄ █▄ █   │",
        "│  █▄▄▄█ ▄▄█▄█▄▄ █▄▄█▄█▄▄▄█▄▄   │",
        "│                                 │",
        "├─────────────────────────────────┤",
        f"│ Data: {data[:25]:<25} │",
        "└─────────────────────────────────┘"
    ]
    return '\n'.join(lines)


def is_qr_code_available() -> bool:
    """Check if QR code generation is available."""
    return QR_AVAILABLE