"""
Model optimization utilities for faster loading
"""
import os
import torch

def optimize_model_loading():
    """Optimize model loading performance"""
    
    # Set environment variables for faster model loading
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # Avoid tokenizer warnings
    os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'  # Cache directory
    os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/tmp/sentence_transformers'  # ST cache
    
    # Create cache directories
    os.makedirs('/tmp/transformers_cache', exist_ok=True)
    os.makedirs('/tmp/sentence_transformers', exist_ok=True)
    
    # Set PyTorch settings for faster inference
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
    
    # Disable gradient computation for inference
    torch.set_grad_enabled(False)

# Call optimization on import
optimize_model_loading()