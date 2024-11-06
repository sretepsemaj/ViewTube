#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    # Set the default settings module for the 'main' entry point.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ViewTube.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Print the current settings being used for verification
    print("Using settings:", os.environ.get('DJANGO_SETTINGS_MODULE'))
    
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
