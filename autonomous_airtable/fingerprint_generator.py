"""
🎭 Генератор уникальных браузерных fingerprint для каждой регистрации

Создает уникальные профили браузера с различными:
- User-Agent (случайные версии Chrome/Edge/Firefox)
- Разрешения экрана
- Геолокации
- Языки
- Timezone
"""
import random
import secrets
from typing import Dict, List, Tuple
from datetime import datetime


class FingerprintGenerator:
    """Генератор уникальных браузерных fingerprint"""
    
    # Списки для генерации случайных данных
    CHROME_VERSIONS = ["120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0", "124.0.0.0"]
    EDGE_VERSIONS = ["120.0.0.0", "121.0.0.0", "122.0.0.0"]
    FIREFOX_VERSIONS = ["122.0", "123.0", "124.0"]
    
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1440, 900), (1536, 864),
        (1600, 900), (1280, 720), (2560, 1440), (1680, 1050)
    ]
    
    PLATFORMS = ["Win32", "MacIntel", "Linux x86_64"]
    
    LANGUAGES = [
        ["en-US", "en"], ["ru-RU", "ru"], ["en-GB", "en"],
        ["de-DE", "de"], ["fr-FR", "fr"], ["es-ES", "es"]
    ]
    
    TIMEZONES = [
        "America/New_York", "Europe/London", "Europe/Moscow",
        "Asia/Tokyo", "America/Los_Angeles", "Europe/Berlin"
    ]
    
    CITIES = {
        "America/New_York": ("New York", 40.7128, -74.0060),
        "Europe/London": ("London", 51.5074, -0.1278),
        "Europe/Moscow": ("Moscow", 55.7558, 37.6173),
        "Asia/Tokyo": ("Tokyo", 35.6762, 139.6503),
        "America/Los_Angeles": ("Los Angeles", 34.0522, -118.2437),
        "Europe/Berlin": ("Berlin", 52.5200, 13.4050)
    }
    
    def __init__(self):
        self.session_id = secrets.token_hex(8)
    
    def _generate_chrome_ua(self) -> str:
        """Генерация User-Agent для Chrome"""
        version = random.choice(self.CHROME_VERSIONS)
        platform = random.choice(["Windows NT 10.0; Win64; x64", "Macintosh; Intel Mac OS X 10_15_7"])
        return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
    
    def _generate_edge_ua(self) -> str:
        """Генерация User-Agent для Edge"""
        version = random.choice(self.EDGE_VERSIONS)
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36 Edg/{version}"
    
    def _generate_firefox_ua(self) -> str:
        """Генерация User-Agent для Firefox"""
        version = random.choice(self.FIREFOX_VERSIONS)
        platform = random.choice(["Windows NT 10.0; Win64; x64", "X11; Linux x86_64", "Macintosh; Intel Mac OS X 10.15"])
        return f"Mozilla/5.0 ({platform}; rv:{version}) Gecko/20100101 Firefox/{version}"
    
    def generate_user_agent(self) -> str:
        """Генерация случайного User-Agent"""
        browser = random.choice(["chrome", "edge", "firefox"])
        
        if browser == "chrome":
            return self._generate_chrome_ua()
        elif browser == "edge":
            return self._generate_edge_ua()
        else:
            return self._generate_firefox_ua()
    
    def generate_screen_resolution(self) -> Tuple[int, int]:
        """Генерация случайного разрешения экрана"""
        return random.choice(self.SCREEN_RESOLUTIONS)
    
    def generate_viewport(self, screen_res: Tuple[int, int]) -> Tuple[int, int]:
        """Генерация viewport (обычно чуть меньше экрана)"""
        width, height = screen_res
        # Вычитаем случайное значение для taskbar/browser chrome
        viewport_width = width - random.randint(0, 50)
        viewport_height = height - random.randint(80, 150)
        return (viewport_width, viewport_height)
    
    def generate_timezone_and_location(self) -> Dict:
        """Генерация timezone и геолокации"""
        timezone = random.choice(self.TIMEZONES)
        city, lat, lon = self.CITIES[timezone]
        
        # Добавляем небольшую случайность к координатам
        lat += random.uniform(-0.1, 0.1)
        lon += random.uniform(-0.1, 0.1)
        
        return {
            "timezone": timezone,
            "city": city,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4)
        }
    
    def generate_canvas_noise(self) -> float:
        """Генерация параметра для Canvas fingerprint шума"""
        return random.uniform(0.00001, 0.0001)
    
    def generate_webgl_vendor(self) -> Tuple[str, str]:
        """Генерация WebGL vendor и renderer"""
        vendors = [
            ("Intel Inc.", "Intel Iris OpenGL Engine"),
            ("NVIDIA Corporation", "NVIDIA GeForce GTX 1650/PCIe/SSE2"),
            ("AMD", "AMD Radeon RX 580 Series"),
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11)")
        ]
        return random.choice(vendors)
    
    def generate_hardware_concurrency(self) -> int:
        """Генерация количества логических процессоров"""
        return random.choice([2, 4, 6, 8, 12, 16])
    
    def generate_device_memory(self) -> int:
        """Генерация объема памяти устройства (GB)"""
        return random.choice([4, 8, 16, 32])
    
    def generate_complete_fingerprint(self) -> Dict:
        """
        Генерация полного уникального fingerprint для браузера
        
        Returns:
            Dict с полным набором параметров для настройки браузера
        """
        screen_res = self.generate_screen_resolution()
        viewport = self.generate_viewport(screen_res)
        timezone_loc = self.generate_timezone_and_location()
        webgl_vendor, webgl_renderer = self.generate_webgl_vendor()
        languages = random.choice(self.LANGUAGES)
        
        fingerprint = {
            # Основные параметры
            "user_agent": self.generate_user_agent(),
            "platform": random.choice(self.PLATFORMS),
            "languages": languages,
            
            # Экран и viewport
            "screen_width": screen_res[0],
            "screen_height": screen_res[1],
            "viewport_width": viewport[0],
            "viewport_height": viewport[1],
            
            # Геолокация и время
            "timezone": timezone_loc["timezone"],
            "city": timezone_loc["city"],
            "latitude": timezone_loc["latitude"],
            "longitude": timezone_loc["longitude"],
            
            # Hardware
            "hardware_concurrency": self.generate_hardware_concurrency(),
            "device_memory": self.generate_device_memory(),
            
            # WebGL
            "webgl_vendor": webgl_vendor,
            "webgl_renderer": webgl_renderer,
            
            # Canvas
            "canvas_noise": self.generate_canvas_noise(),
            
            # Дополнительные параметры
            "color_depth": random.choice([24, 32]),
            "pixel_ratio": random.choice([1, 1.5, 2]),
            "session_id": self.session_id,
            "generated_at": datetime.now().isoformat()
        }
        
        return fingerprint
    
    def to_playwright_context_args(self, fingerprint: Dict) -> Dict:
        """
        Конвертация fingerprint в аргументы для playwright context
        
        Args:
            fingerprint: Словарь с fingerprint данными
            
        Returns:
            Dict для передачи в browser.new_context(**args)
        """
        return {
            "user_agent": fingerprint["user_agent"],
            "viewport": {
                "width": fingerprint["viewport_width"],
                "height": fingerprint["viewport_height"]
            },
            "screen": {
                "width": fingerprint["screen_width"],
                "height": fingerprint["screen_height"]
            },
            "locale": fingerprint["languages"][0],
            "timezone_id": fingerprint["timezone"],
            "geolocation": {
                "latitude": fingerprint["latitude"],
                "longitude": fingerprint["longitude"]
            },
            "permissions": ["geolocation"],
            "color_scheme": random.choice(["light", "dark"]),
            "device_scale_factor": fingerprint["pixel_ratio"]
        }
    
    def print_fingerprint(self, fingerprint: Dict):
        """Красивый вывод fingerprint в консоль"""
        print("\n" + "="*70)
        print("🎭 СГЕНЕРИРОВАННЫЙ FINGERPRINT")
        print("="*70)
        print(f"🔑 Session ID: {fingerprint['session_id']}")
        print(f"🌍 Location: {fingerprint['city']} ({fingerprint['latitude']}, {fingerprint['longitude']})")
        print(f"⏰ Timezone: {fingerprint['timezone']}")
        print(f"💻 User-Agent: {fingerprint['user_agent'][:80]}...")
        print(f"📺 Screen: {fingerprint['screen_width']}x{fingerprint['screen_height']}")
        print(f"🖥️  Viewport: {fingerprint['viewport_width']}x{fingerprint['viewport_height']}")
        print(f"🎨 WebGL: {fingerprint['webgl_vendor']} / {fingerprint['webgl_renderer'][:50]}...")
        print(f"🧠 CPU Cores: {fingerprint['hardware_concurrency']}")
        print(f"💾 Memory: {fingerprint['device_memory']}GB")
        print(f"🗣️  Languages: {', '.join(fingerprint['languages'])}")
        print("="*70 + "\n")


# Функция для быстрого использования
def generate_unique_fingerprint() -> Dict:
    """
    Быстрая генерация уникального fingerprint
    
    Returns:
        Dict с полным набором параметров
        
    Example:
        >>> fp = generate_unique_fingerprint()
        >>> print(fp['user_agent'])
    """
    generator = FingerprintGenerator()
    return generator.generate_complete_fingerprint()


if __name__ == "__main__":
    # Тест модуля
    print("\n🧪 ТЕСТИРОВАНИЕ FINGERPRINT GENERATOR\n")
    
    generator = FingerprintGenerator()
    
    # Генерируем 3 разных fingerprint
    for i in range(3):
        print(f"\n{'='*70}")
        print(f"FINGERPRINT #{i+1}")
        print(f"{'='*70}")
        
        fp = generator.generate_complete_fingerprint()
        generator.print_fingerprint(fp)
        
        print("\n📋 Playwright Context Args:")
        args = generator.to_playwright_context_args(fp)
        for key, value in args.items():
            print(f"   • {key}: {value}")
        
        # Новый session_id для следующей итерации
        generator.session_id = secrets.token_hex(8)
    
    print("\n✅ Тестирование завершено!")
