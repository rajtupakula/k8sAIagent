#!/usr/bin/env python3
"""
Container-Safe RAG Agent Initializer
Handles ChromaDB and other dependency issues in containerized environments
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def safe_chromadb_init():
    """Safely initialize ChromaDB with container-friendly settings"""
    try:
        # Set environment variables to prevent ChromaDB issues
        os.environ["CHROMA_TELEMETRY"] = "false"
        os.environ["ANONYMIZED_TELEMETRY"] = "false"
        os.environ["CHROMA_SERVER_NOFILE"] = "65536"
        
        # Import and test ChromaDB
        import chromadb
        from chromadb.config import Settings
        
        # Test with container-safe settings
        test_settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=False,
            chroma_server_nofile=65536
        )
        
        test_client = chromadb.Client(test_settings)
        logger.info("✅ ChromaDB initialized successfully")
        return True, chromadb
        
    except Exception as e:
        logger.warning(f"⚠️ ChromaDB initialization failed: {e}")
        logger.info("🔄 Falling back to offline mode without vector search")
        return False, None

def safe_sentence_transformers_init():
    """Safely initialize SentenceTransformers with CPU-only settings"""
    try:
        # Set environment for CPU-only operation
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        from sentence_transformers import SentenceTransformer
        logger.info("✅ SentenceTransformer imported successfully")
        return True, SentenceTransformer
        
    except Exception as e:
        logger.warning(f"⚠️ SentenceTransformer initialization failed: {e}")
        logger.info("🔄 Falling back to basic text processing")
        return False, None

def safe_imports():
    """Perform all safe imports for container environment"""
    results = {}
    
    # Test ChromaDB
    chromadb_ok, chromadb_module = safe_chromadb_init()
    results['chromadb'] = {'available': chromadb_ok, 'module': chromadb_module}
    
    # Test SentenceTransformers
    st_ok, st_module = safe_sentence_transformers_init()
    results['sentence_transformers'] = {'available': st_ok, 'module': st_module}
    
    # Test other dependencies
    try:
        import requests
        results['requests'] = {'available': True, 'module': requests}
        logger.info("✅ Requests available")
    except ImportError:
        results['requests'] = {'available': False, 'module': None}
        logger.warning("⚠️ Requests not available")
    
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        results['langchain'] = {'available': True, 'module': RecursiveCharacterTextSplitter}
        logger.info("✅ LangChain available")
    except ImportError:
        results['langchain'] = {'available': False, 'module': None}
        logger.warning("⚠️ LangChain not available")
    
    return results

def main():
    """Test all dependencies and report status"""
    logger.info("🔍 Testing container dependencies...")
    
    results = safe_imports()
    
    logger.info("📊 Dependency Status Report:")
    for dep, info in results.items():
        status = "✅ Available" if info['available'] else "❌ Not Available"
        logger.info(f"  • {dep}: {status}")
    
    # Determine operational mode
    if results['chromadb']['available'] and results['sentence_transformers']['available']:
        mode = "🚀 Full AI Mode"
    elif results['sentence_transformers']['available']:
        mode = "🤖 Basic AI Mode (no vector search)"
    else:
        mode = "📝 Offline Mode (text processing only)"
    
    logger.info(f"🎯 Operational Mode: {mode}")
    
    return results

if __name__ == "__main__":
    main()
