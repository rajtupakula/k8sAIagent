#!/usr/bin/env python3
"""
Telemetry disabling utility for ChromaDB and other services
This module provides comprehensive telemetry disabling for offline operation
"""

import os
import logging


def disable_all_telemetry():
    """Disable telemetry for all services that might send data."""
    logger = logging.getLogger(__name__)
    
    # ChromaDB telemetry
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ["CHROMA_TELEMETRY"] = "False"
    os.environ["CHROMA_SERVER_NOFILE"] = "1048576"
    
    # HuggingFace telemetry
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    
    # Streamlit telemetry
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "False"
    os.environ["STREAMLIT_SERVER_PORT"] = "8080"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
    
    # Disable various analytics and telemetry
    os.environ["DO_NOT_TRACK"] = "1"
    os.environ["DISABLE_TELEMETRY"] = "1"
    
    # Python specific
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    
    # Try to disable ChromaDB telemetry at import time
    try:
        # Set the telemetry environment before any imports
        import sys
        if 'chromadb' not in sys.modules:
            # Monkey patch the telemetry module before import
            import types
            
            # Create a dummy posthog module
            dummy_posthog = types.ModuleType('posthog')
            dummy_posthog.capture = lambda *args, **kwargs: None
            dummy_posthog.identify = lambda *args, **kwargs: None
            dummy_posthog.alias = lambda *args, **kwargs: None
            dummy_posthog.set = lambda *args, **kwargs: None
            
            sys.modules['posthog'] = dummy_posthog
            
            logger.debug("ChromaDB telemetry disabled at import level")
    except Exception as e:
        logger.debug(f"Could not pre-disable ChromaDB telemetry: {e}")
    
    logger.info("All telemetry disabled for offline operation")


def disable_chromadb_telemetry():
    """Specifically disable ChromaDB telemetry after import."""
    logger = logging.getLogger(__name__)
    
    try:
        # Try to disable posthog in chromadb telemetry module
        import chromadb.telemetry.product.posthog as posthog_telemetry
        
        # Replace the posthog client with a dummy
        class DummyPosthog:
            def capture(self, *args, **kwargs):
                pass
            def identify(self, *args, **kwargs):
                pass
            def alias(self, *args, **kwargs):
                pass
            def set(self, *args, **kwargs):
                pass
        
        posthog_telemetry.posthog = DummyPosthog()
        logger.debug("ChromaDB posthog telemetry disabled")
        
    except ImportError:
        logger.debug("ChromaDB telemetry module not available")
    except Exception as e:
        logger.debug(f"Could not disable ChromaDB telemetry: {e}")


if __name__ == "__main__":
    # Test the telemetry disabling
    logging.basicConfig(level=logging.DEBUG)
    disable_all_telemetry()
    disable_chromadb_telemetry()
    print("Telemetry disabled successfully")
