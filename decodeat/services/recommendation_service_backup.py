"""
Backup of original recommendation service before refactoring.
"""
from typing import List, Dict, Any, Optional
import numpy as np

from decodeat.services.vector_service import VectorService
from decodeat.utils.logging import LoggingService
from decodeat.utils.performance import measure_time, recommendation_cache

logger = LoggingService(__name__)


class OriginalRecommendationService:
    """Original recommendation service implementation (backup)"""
    
    # 사용자 행동별 가중치 (요구사항에 따라 정의됨)
    BEHAVIOR_WEIGHTS = {
        'REGISTER': 5,  # 직접 등록 = 가장 강한 관심
        'LIKE': 3,      # 좋아요 = 선호
        'SEARCH': 2,    # 검색 = 관심
        'VIEW': 1       # 조회 = 기본 관심
    }
    
    def __init__(self, vector_service: VectorService):
        """
        추천 서비스를 초기화합니다.
        
        Args:
            vector_service: 유사도 검색을 위한 벡터 서비스 인스턴스
        """
        self.vector_service = vector_service