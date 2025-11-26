"""Translation manager for HandForge."""

import json
import os
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QLocale, QTranslator, QCoreApplication


class Translator:
    """Manages translations for the application."""
    
    SUPPORTED_LOCALES = {
        'en': 'English',
        'ru': 'Russian',
        'pt': 'Portuguese',
        'es': 'Spanish',
        'et': 'Estonian',
        'fr': 'French',
        'de': 'German',
        'ja': 'Japanese',
        'zh': 'Chinese',
        'ko': 'Korean',
        'id': 'Indonesian',
    }
    
    def __init__(self, locale: str = 'en'):
        """Initialize translator with locale."""
        self.locale = locale
        self.translations: Dict[str, str] = {}
        self.qt_translator: Optional[QTranslator] = None
        self.load_translations()
    
    def load_translations(self):
        """Load translations for current locale."""
        locale_dir = Path(__file__).parent / 'locales'
        locale_file = locale_dir / f'{self.locale}.json'
        
        if locale_file.exists():
            with open(locale_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        else:
            # Fallback to English
            en_file = locale_dir / 'en.json'
            if en_file.exists():
                with open(en_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
    
    def translate(self, key: str, default: Optional[str] = None) -> str:
        """Translate a key to current locale."""
        return self.translations.get(key, default or key)
    
    def tr(self, key: str, default: Optional[str] = None) -> str:
        """Alias for translate."""
        return self.translate(key, default)
    
    def set_locale(self, locale: str):
        """Change locale and reload translations."""
        if locale in self.SUPPORTED_LOCALES:
            self.locale = locale
            self.load_translations()
    
    @staticmethod
    def detect_system_locale() -> str:
        """Detect system locale."""
        system_locale = QLocale.system().name()
        # Extract language code (e.g., 'en_US' -> 'en')
        lang_code = system_locale.split('_')[0]
        
        # Map to supported locales
        if lang_code in Translator.SUPPORTED_LOCALES:
            return lang_code
        
        # Default to English
        return 'en'


# Global translator instance
_translator_instance: Optional[Translator] = None


def get_translator(locale: Optional[str] = None) -> Translator:
    """Get or create translator instance."""
    global _translator_instance
    
    if _translator_instance is None:
        if locale is None:
            locale = Translator.detect_system_locale()
        _translator_instance = Translator(locale)
    elif locale is not None and locale != _translator_instance.locale:
        _translator_instance.set_locale(locale)
    
    return _translator_instance


def set_locale(locale: str):
    """Set global locale."""
    translator = get_translator()
    translator.set_locale(locale)

