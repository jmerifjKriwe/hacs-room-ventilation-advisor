#!/usr/bin/env python3
"""
Home Assistant Custom Component Language File Manager
Automatisiert die Erstellung und Verwaltung von Translation Files
"""

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class HALanguageManager:
    def __init__(self, component_path: str | None = None):
        if component_path is None:
            component_path = self.find_component_directory()

        self.component_path = Path(component_path)
        self.translations_path = self.component_path / "translations"
        self.translations_path.mkdir(exist_ok=True)

        # Standard Sprachen für Home Assistant
        self.default_languages = ["en", "de", "fr", "es", "it", "nl", "pl", "pt", "ru"]

        # Standard Translation Keys für HA Components
        self.standard_keys = {
            "config": {
                "step": {
                    "user": {
                        "title": "Setup",
                        "description": "Configure your component",
                        "data": {},
                    }
                },
                "error": {
                    "cannot_connect": "Failed to connect",
                    "invalid_auth": "Invalid authentication",
                    "unknown": "Unknown error occurred",
                },
                "abort": {"already_configured": "Device is already configured"},
            },
            "options": {"step": {"init": {"title": "Options", "data": {}}}},
            "entity": {},
            "device_automation": {},
        }

    def find_component_directory(self) -> str:
        """Findet automatisch das Component-Verzeichnis"""
        current_dir = Path.cwd()

        # Suche nach custom_components Verzeichnis im aktuellen Pfad oder in Unterverzeichnissen
        search_paths = [
            current_dir,
            current_dir / "custom_components",
            current_dir.parent / "custom_components"
            if current_dir.parent != current_dir
            else None,
        ]

        # Entferne None-Werte
        search_paths = [p for p in search_paths if p is not None]

        for search_path in search_paths:
            if search_path.exists():
                # Prüfe ob es direkt ein Component ist (hat manifest.json)
                if (search_path / "manifest.json").exists():
                    logger.info(f"Component gefunden: {search_path}")
                    return str(search_path)

                # Prüfe ob es custom_components Verzeichnis ist
                if search_path.name == "custom_components":
                    # Finde alle Unterverzeichnisse mit manifest.json
                    components = [
                        d
                        for d in search_path.iterdir()
                        if d.is_dir() and (d / "manifest.json").exists()
                    ]

                    if len(components) == 1:
                        logger.info(f"Component automatisch erkannt: {components[0]}")
                        return str(components[0])
                    if len(components) > 1:
                        print(f"Mehrere Components gefunden in {search_path}:")
                        for i, comp in enumerate(components, 1):
                            print(f"  {i}. {comp.name}")

                        # Lass Benutzer wählen
                        try:
                            choice = (
                                int(input("Wählen Sie eine Component (Nummer): ")) - 1
                            )
                            if 0 <= choice < len(components):
                                logger.info(f"Component gewählt: {components[choice]}")
                                return str(components[choice])
                        except (ValueError, IndexError):
                            pass

                        raise ValueError("Ungültige Auswahl")

                # Durchsuche Unterverzeichnisse nach Components
                for subdir in search_path.iterdir():
                    if subdir.is_dir() and (subdir / "manifest.json").exists():
                        logger.info(f"Component gefunden: {subdir}")
                        return str(subdir)

        # Fallback: Suche nach typischen Component-Dateien im aktuellen Verzeichnis
        component_files = ["__init__.py", "manifest.json", "config_flow.py"]
        if any((current_dir / f).exists() for f in component_files):
            logger.info(f"Component im aktuellen Verzeichnis erkannt: {current_dir}")
            return str(current_dir)

        raise ValueError(
            "Kein Home Assistant Component gefunden!\n"
            "Führen Sie das Script aus:\n"
            "- Im Component-Verzeichnis\n"
            "- Im custom_components Verzeichnis\n"
            "- Oder geben Sie den Pfad explizit an"
        )

        # Standard Translation Keys für HA Components
        self.standard_keys = {
            "config": {
                "step": {
                    "user": {
                        "title": "Setup",
                        "description": "Configure your component",
                        "data": {},
                    }
                },
                "error": {
                    "cannot_connect": "Failed to connect",
                    "invalid_auth": "Invalid authentication",
                    "unknown": "Unknown error occurred",
                },
                "abort": {"already_configured": "Device is already configured"},
            },
            "options": {"step": {"init": {"title": "Options", "data": {}}}},
            "entity": {},
            "device_automation": {},
        }

    def scan_translation_keys(self) -> set[str]:
        """Scannt den Component Code nach Translation Keys"""
        keys = set()

        # Regex Patterns für häufige Translation Key Verwendungen
        patterns = [
            r'hass\.localize\(["\']([^"\']+)["\']',  # hass.localize("key")
            r'translation_key\s*=\s*["\']([^"\']+)["\']',  # translation_key = "key"
            r'_attr_translation_key\s*=\s*["\']([^"\']+)["\']',  # _attr_translation_key = "key"
            r'async_translate\(["\']([^"\']+)["\']',  # async_translate("key")
            r'["\']translation_key["\']:\s*["\']([^"\']+)["\']',  # "translation_key": "key"
        ]

        # Durchsuche alle Python Dateien im Component
        for py_file in self.component_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    keys.update(matches)

            except Exception as e:
                logger.warning(f"Fehler beim Lesen von {py_file}: {e}")

        return keys

    def extract_config_flow_keys(self) -> dict[str, Any]:
        """Extrahiert spezielle Keys aus config_flow.py"""
        config_flow_path = self.component_path / "config_flow.py"
        keys = {"config": {"step": {}, "error": {}, "abort": {}}}

        if not config_flow_path.exists():
            return keys

        try:
            with open(config_flow_path, encoding="utf-8") as f:
                content = f.read()

            # Suche nach Step Definitionen
            step_matches = re.findall(r"async def async_step_(\w+)", content)
            for step in step_matches:
                keys["config"]["step"][step] = {
                    "title": f"{step.title()} Step",
                    "description": f"Configure {step} settings",
                    "data": {},
                }

            # Suche nach Error Keys
            error_matches = re.findall(r'errors\[["\'](\w+)["\']\]', content)
            for error in error_matches:
                keys["config"]["error"][error] = f"Error: {error}"

            # Suche nach Abort Reasons
            abort_matches = re.findall(r'async_abort\(reason=["\'](\w+)["\']', content)
            for abort in abort_matches:
                keys["config"]["abort"][abort] = f"Aborted: {abort}"

        except Exception as e:
            logger.warning(f"Fehler beim Parsen von config_flow.py: {e}")

        return keys

    def load_existing_translations(self, language: str) -> dict[str, Any]:
        """Lädt existierende Übersetzungen für eine Sprache"""
        lang_file = self.translations_path / f"{language}.json"

        if lang_file.exists():
            try:
                with open(lang_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Fehler beim Laden von {lang_file}: {e}")

        return {}

    def save_translations(self, language: str, translations: dict[str, Any]):
        """Speichert Übersetzungen in eine Datei"""
        lang_file = self.translations_path / f"{language}.json"

        try:
            with open(lang_file, "w", encoding="utf-8") as f:
                json.dump(translations, f, indent=2, ensure_ascii=False)
            logger.info(f"Gespeichert: {lang_file}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern von {lang_file}: {e}")

    def merge_translations(
        self, existing: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """Mergt neue Keys in existierende Übersetzungen"""

        def deep_merge(base: dict, update: dict) -> dict:
            result = base.copy()
            for key, value in update.items():
                if (
                    key in result
                    and isinstance(result[key], dict)
                    and isinstance(value, dict)
                ):
                    result[key] = deep_merge(result[key], value)
                elif key not in result:
                    result[key] = value
            return result

        return deep_merge(existing, new)

    def create_language_files(self, languages: list[str] | None = None):
        """Erstellt oder aktualisiert Language Files"""
        if languages is None:
            languages = self.default_languages

        # Scanne nach verwendeten Keys
        scanned_keys = self.scan_translation_keys()
        logger.info(f"Gefundene Translation Keys: {len(scanned_keys)}")

        # Extrahiere Config Flow Keys
        config_keys = self.extract_config_flow_keys()

        # Kombiniere Standard Keys mit gefundenen Keys
        base_structure = self.standard_keys.copy()
        base_structure = self.merge_translations(base_structure, config_keys)

        # Füge gefundene Keys zur Entity Sektion hinzu
        for key in scanned_keys:
            if "." in key:
                # Hierarchische Keys (z.B. "sensor.temperature")
                parts = key.split(".")
                current = base_structure["entity"]
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = {"name": parts[-1].replace("_", " ").title()}
            else:
                # Einfache Keys
                base_structure["entity"][key] = {"name": key.replace("_", " ").title()}

        # Erstelle/aktualisiere Dateien für jede Sprache
        for lang in languages:
            existing = self.load_existing_translations(lang)
            merged = self.merge_translations(existing, base_structure)
            self.save_translations(lang, merged)

    def check_missing_keys(self) -> dict[str, list[str]]:
        """Prüft auf fehlende Keys zwischen verschiedenen Sprachen"""
        missing_keys = {}
        lang_files = list(self.translations_path.glob("*.json"))

        if not lang_files:
            return missing_keys

        # Lade alle Übersetzungen
        all_translations = {}
        for lang_file in lang_files:
            lang = lang_file.stem
            all_translations[lang] = self.load_existing_translations(lang)

        # Finde alle Keys aus allen Sprachen
        all_keys = set()

        def extract_keys(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_key = f"{prefix}.{key}" if prefix else key
                    all_keys.add(current_key)
                    extract_keys(value, current_key)

        for translations in all_translations.values():
            extract_keys(translations)

        # Prüfe fehlende Keys pro Sprache
        for lang, translations in all_translations.items():
            lang_keys = set()
            extract_keys(translations)
            missing_keys[lang] = list(all_keys - lang_keys)

        return missing_keys

    def generate_report(self):
        """Generiert einen Bericht über den Status der Übersetzungen"""
        print("\n=== Home Assistant Translation Report ===")
        print(f"Component Path: {self.component_path}")
        print(f"Translations Path: {self.translations_path}")

        # Scanned Keys
        scanned_keys = self.scan_translation_keys()
        print(f"\nGefundene Translation Keys im Code: {len(scanned_keys)}")
        for key in sorted(scanned_keys):
            print(f"  - {key}")

        # Existing Language Files
        lang_files = list(self.translations_path.glob("*.json"))
        print(f"\nVorhandene Sprachdateien: {len(lang_files)}")
        for lang_file in lang_files:
            translations = self.load_existing_translations(lang_file.stem)
            key_count = sum(1 for _ in self._count_keys(translations))
            print(f"  - {lang_file.name}: {key_count} Keys")

        # Missing Keys
        missing = self.check_missing_keys()
        if any(missing.values()):
            print("\nFehlende Keys:")
            for lang, keys in missing.items():
                if keys:
                    print(f"  {lang}: {len(keys)} fehlende Keys")

    def _count_keys(self, obj):
        """Hilfsfunktion zum Zählen aller Keys in einem verschachtelten Dict"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                yield key
                yield from self._count_keys(value)


def main():
    parser = argparse.ArgumentParser(
        description="Home Assistant Custom Component Language File Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s --report
    Automatische Erkennung und Report für gefundene Component

  %(prog)s /path/to/component --create
    Erstellt Standard Language Files für spezifische Component

  %(prog)s /path/to/component --create -l en de
    Erstellt nur Englisch und Deutsch Language Files

  %(prog)s /path/to/component --report
    Zeigt einen detaillierten Report über vorhandene Übersetzungen

  %(prog)s /path/to/component --check
    Prüft auf fehlende Keys zwischen verschiedenen Sprachen

  %(prog)s /path/to/component --create --report
    Erstellt Language Files und zeigt anschließend einen Report

Das Script scannt automatisch nach Translation Keys im Code und erstellt
die entsprechenden JSON-Strukturen für Home Assistant Components.
        """,
    )

    parser.add_argument(
        "component_path",
        nargs="?",
        help="Pfad zum Custom Component Verzeichnis (optional - wird automatisch erkannt)",
    )
    parser.add_argument(
        "--languages",
        "-l",
        nargs="+",
        help="Sprachen (Standard: en de fr es it nl pl pt ru)",
    )
    parser.add_argument(
        "--create",
        "-c",
        action="store_true",
        help="Erstelle/aktualisiere Language Files",
    )
    parser.add_argument(
        "--report",
        "-r",
        action="store_true",
        help="Zeige detaillierten Übersetzungsreport",
    )
    parser.add_argument(
        "--check", action="store_true", help="Prüfe auf fehlende Keys zwischen Sprachen"
    )

    args = parser.parse_args()

    # Prüfe ob Pfad existiert (falls angegeben)
    if args.component_path and not os.path.exists(args.component_path):
        logger.error(f"Component Pfad existiert nicht: {args.component_path}")
        print(
            "\nStellen Sie sicher, dass der Pfad zu Ihrem Custom Component korrekt ist."
        )
        return 1

    # Prüfe ob mindestens eine Aktion gewählt wurde
    if not any([args.create, args.report, args.check]):
        print("Fehler: Mindestens eine Aktion muss gewählt werden!\n")
        parser.print_help()
        return 1

    try:
        manager = HALanguageManager(args.component_path)
    except ValueError as e:
        logger.error(str(e))
        return 1

    if args.create:
        component_name = manager.component_path.name
        print(
            f"Erstelle Language Files für Component '{component_name}': {manager.component_path}"
        )
        manager.create_language_files(args.languages)
        print("✓ Language Files erfolgreich erstellt/aktualisiert")

    if args.report:
        manager.generate_report()

    if args.check:
        missing = manager.check_missing_keys()
        if any(missing.values()):
            print("\n⚠️  Fehlende Keys gefunden:")
            for lang, keys in missing.items():
                if keys:
                    print(
                        f"  {lang}: {', '.join(keys[:5])}"
                        + (f" ... und {len(keys) - 5} weitere" if len(keys) > 5 else "")
                    )
        else:
            print("\n✓ Keine fehlenden Keys gefunden!")

    return 0


if __name__ == "__main__":
    exit(main())
