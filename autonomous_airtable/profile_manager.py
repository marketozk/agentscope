"""
🎭 Менеджер полноценных браузерных профилей

Создает реалистичные профили браузера с:
- Persistent storage (cookies, localStorage, cache)
- Browser history
- Extensions
- Fonts
- Canvas/WebGL fingerprints
- Realistic timing patterns
"""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, Optional
import secrets
from datetime import datetime


class ProfileManager:
    """Управление полноценными браузерными профилями"""
    
    def __init__(self, profiles_dir: str = "browser_profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)
        
    def create_profile(self, profile_id: Optional[str] = None) -> Dict:
        """
        Создать новый полноценный профиль браузера
        
        Returns:
            Dict с путем к профилю и метаданными
        """
        if not profile_id:
            profile_id = f"profile_{secrets.token_hex(8)}"
        
        profile_path = self.profiles_dir / profile_id
        profile_path.mkdir(exist_ok=True)
        
        # Создаем структуру профиля
        (profile_path / "Default").mkdir(exist_ok=True)
        (profile_path / "Default" / "Local Storage").mkdir(exist_ok=True)
        (profile_path / "Default" / "Session Storage").mkdir(exist_ok=True)
        (profile_path / "Default" / "Cache").mkdir(exist_ok=True)
        
        # Preferences для Chromium
        preferences = {
            "profile": {
                "name": f"User_{secrets.token_hex(4)}",
                "default_content_setting_values": {
                    "notifications": 2,  # Block
                    "geolocation": 1,    # Allow
                },
                "exit_type": "Normal",
                "password_manager_enabled": False,
            },
            "credentials_enable_service": False,
            "download": {
                "prompt_for_download": False,
            },
            "safebrowsing": {
                "enabled": True
            },
            "browser": {
                "check_default_browser": False,
            },
            "distribution": {
                "skip_first_run_ui": True,
                "show_welcome_page": False,
                "import_history": False,
                "import_bookmarks": False,
                "import_search_engine": False,
            },
            "first_run_tabs": [],
        }
        
        prefs_file = profile_path / "Default" / "Preferences"
        with open(prefs_file, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2)
        
        # Local State для Chromium
        local_state = {
            "profile": {
                "info_cache": {
                    "Default": {
                        "name": f"User_{secrets.token_hex(4)}",
                    }
                },
                "last_used": "Default",
            }
        }
        
        local_state_file = profile_path / "Local State"
        with open(local_state_file, 'w', encoding='utf-8') as f:
            json.dump(local_state, f, indent=2)
        
        # Метаданные профиля
        metadata = {
            "profile_id": profile_id,
            "profile_path": str(profile_path.absolute()),
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "registration_count": 0,
        }
        
        metadata_file = profile_path / "profile_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Создан профиль: {profile_id}")
        print(f"   📂 Путь: {profile_path.absolute()}")
        
        return metadata
    
    def get_profile_path(self, profile_id: str) -> Optional[Path]:
        """Получить путь к профилю"""
        profile_path = self.profiles_dir / profile_id
        if profile_path.exists():
            return profile_path
        return None
    
    def update_profile_metadata(self, profile_id: str, updates: Dict):
        """Обновить метаданные профиля"""
        profile_path = self.get_profile_path(profile_id)
        if not profile_path:
            return
        
        metadata_file = profile_path / "profile_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata.update(updates)
            metadata["last_used"] = datetime.now().isoformat()
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
    
    def delete_profile(self, profile_id: str):
        """Удалить профиль"""
        profile_path = self.get_profile_path(profile_id)
        if profile_path:
            shutil.rmtree(profile_path)
            print(f"🗑️  Удален профиль: {profile_id}")
    
    def list_profiles(self) -> list:
        """Список всех профилей"""
        profiles = []
        for item in self.profiles_dir.iterdir():
            if item.is_dir():
                metadata_file = item / "profile_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        profiles.append(json.load(f))
        return profiles
    
    def cleanup_old_profiles(self, max_age_days: int = 7):
        """Удалить старые профили"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for profile in self.list_profiles():
            created_at = datetime.fromisoformat(profile["created_at"])
            if created_at < cutoff_date:
                self.delete_profile(profile["profile_id"])


def generate_realistic_user_data() -> Dict:
    """Генерация реалистичных пользовательских данных для профиля"""
    import random
    
    first_names = ["John", "Jane", "Michael", "Emily", "David", "Sarah", "James", "Emma"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
    
    return {
        "first_name": random.choice(first_names),
        "last_name": random.choice(last_names),
        "timezone": random.choice([
            "America/New_York", "Europe/London", "America/Los_Angeles",
            "America/Chicago", "Europe/Paris", "Asia/Tokyo"
        ]),
        "language": random.choice(["en-US", "en-GB", "en-CA"]),
    }


if __name__ == "__main__":
    # Тест
    manager = ProfileManager()
    
    print("\n🧪 Тестирование ProfileManager\n")
    
    # Создаем профиль
    profile = manager.create_profile()
    
    print(f"\n📋 Метаданные профиля:")
    for key, value in profile.items():
        print(f"   {key}: {value}")
    
    # Список профилей
    print(f"\n📂 Всего профилей: {len(manager.list_profiles())}")
    
    print("\n✅ Тест завершен!")
