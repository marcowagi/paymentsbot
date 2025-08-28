"""
Internationalization utility for the Telegram Finance Bot
Provides translation services based on user language preference
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
from config import TRANSLATIONS_DIR, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class I18n:
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.load_translations()
    
    def load_translations(self):
        """Load translation files from translations directory"""
        try:
            for lang_file in TRANSLATIONS_DIR.glob("*.json"):
                lang_code = lang_file.stem
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
                logger.info(f"Loaded translations for language: {lang_code}")
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
            # Create minimal fallback translations
            self.translations = {
                "ar": {"error": "حدث خطأ"},
                "en": {"error": "An error occurred"}
            }
    
    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Get translated text for a key
        
        Args:
            key: Translation key
            lang: Language code (defaults to DEFAULT_LANGUAGE)
            **kwargs: Variables to format into the translation string
        
        Returns:
            Translated and formatted string
        """
        if lang is None:
            lang = DEFAULT_LANGUAGE
        
        # Fallback to default language if specified language not available
        if lang not in self.translations:
            lang = DEFAULT_LANGUAGE
        
        # Fallback to English if default language not available
        if lang not in self.translations:
            lang = "en"
        
        # Get translation or return key as fallback
        translation = self.translations.get(lang, {}).get(key, key)
        
        # Format with provided variables
        try:
            return translation.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.warning(f"Error formatting translation '{key}' for language '{lang}': {e}")
            return translation

# Global instance
i18n = I18n()

def _(key: str, lang: str = None, **kwargs) -> str:
    """Shorthand function for getting translations"""
    return i18n.get(key, lang, **kwargs)