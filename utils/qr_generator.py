import qrcode
from io import BytesIO
from PIL import Image
import base64

class QRGenerator:
    """Класс для генерации QR-кодов с различными настройками"""
    
    @staticmethod
    def generate_qr_code(data: str, size: int = 300, version: int = 7) -> BytesIO:
        """
        Генерирует QR-код и возвращает BytesIO объект
        
        Args:
            data (str): Данные для кодирования
            size (int): Размер изображения
            version (int): Версия QR-кода (1-40)
            
        Returns:
            BytesIO: Поток с изображением PNG
        """
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Изменяем размер если нужно
        if size != 300:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io
    
    @staticmethod
    def generate_qr_base64(data: str, size: int = 300) -> str:
        """
        Генерирует QR-код и возвращает base64 строку
        
        Args:
            data (str): Данные для кодирования
            size (int): Размер изображения
            
        Returns:
            str: Base64 строка с изображением
        """
        qr_io = QRGenerator.generate_qr_code(data, size)
        return base64.b64encode(qr_io.getvalue()).decode('utf-8')
    
    @staticmethod
    def validate_data(data: str) -> bool:
        """
        Проверяет данные для QR-кода
        
        Args:
            data (str): Данные для проверки
            
        Returns:
            bool: True если данные валидны
        """
        if not data or not isinstance(data, str):
            return False
        
        # Максимальная длина для QR-кода версии 7 с коррекцией ошибок L
        max_length = 154  # для цифровых данных
        return len(data) <= max_length
