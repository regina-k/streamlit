"""
아파트 가치 상승률 ML 예측 모듈. (장원준 담당)

현재 STUB 상태 — 더미 데이터를 반환하므로 UI 연동은 즉시 가능하다.
장원준이 LightGBM/XGBoost 모델 학습 후 내부 구현을 채울 것.
함수 시그니처(입출력 타입)는 변경 금지.
"""

from config import MODELS_DIR


def predict_price_growth(
    region: str,
    area_type: str,
    horizon: str,
    current_index: float | None = None,
) -> dict:
    """아파트 가치 상승률을 예측한다.

    Args:
        region: 지역명. 예) '서울 강남'
        area_type: 평형 구분. config.AREA_TYPES 참고. 예) '60㎡이하'
        horizon: 예측 기간. '1yr' | '3yr' | '5yr'
        current_index: 현재 KB지수. None이면 데이터에서 자동 조회.

    Returns:
        {
            'region': str,
            'horizon': str,
            'predicted_growth_pct': float,  # 예측 상승률 (%)
            'confidence': str,              # 'high' | 'medium' | 'low'
            'model_version': str,
            'note': str,
        }
    """
    # TODO (장원준): load_model()로 모델 로드 후 피처 벡터 구성 → predict
    # TODO (장원준): current_index가 None이면 data_loader.load_ml_timeseries()에서 최신값 조회
    return {
        "region": region,
        "horizon": horizon,
        "predicted_growth_pct": 0.0,
        "confidence": "low",
        "model_version": "STUB_v0",
        "note": "⚠️ ML 모델 미학습 상태 — 더미 데이터입니다",
    }


def load_model(model_path: str | None = None):
    """학습된 ML 모델을 로드한다.

    Args:
        model_path: 모델 파일 경로. None이면 config.MODELS_DIR 기본 경로 사용.

    Returns:
        로드된 모델 객체. STUB 상태에서는 None 반환.
    """
    # TODO (장원준): joblib.load() 또는 lgb.Booster().load_model() 구현
    return None
