#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

def main():
    """Run administrative tasks."""
    # プロジェクトルートをPYTHONPATHに追加
    project_root = Path(__file__).resolve().parent
    sys.path.append(str(project_root))
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Djangoをインストールできませんでした。"
            "pip install djangoを実行してください。"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main() 