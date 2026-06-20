"""
LangChain RAG 기반 AI 어드바이저 모듈. (김동하 담당)

현재 STUB 상태 — _stub_gpt_response()가 GPT 직접 호출로 임시 동작한다.
김동하가 LangChain RAG 파이프라인 완성 후 get_loan_advice() 내부를 교체할 것.
함수 시그니처(입출력 타입)는 변경 금지.
"""

from config import VECTOR_STORE_DIR


def get_loan_advice(
    user_profile: dict,
    target_apt: dict,
    ml_prediction: dict,
) -> str:
    """LangChain RAG 기반 맞춤형 대출·투자 어드바이저 응답을 생성한다.

    Args:
        user_profile: 고객 투자 유형 프로파일.
            {
                'household_type': str,      # config.HOUSEHOLD_TYPES 참고
                'purpose': str,             # '실거주' | '투자'
                'available_cash_man': int,  # 가용자본금 (만원)
                'annual_income_man': int,   # 부부합산연소득 (만원)
                'existing_loan_man': int,   # 현재 보유 대출 (만원)
            }
        target_apt: 선택 아파트 정보.
            {
                'name': str,
                'address': str,
                'price_man': int,
                'area': str,
                'units': int,
                'completion': str,
            }
        ml_prediction: ml_predictor.predict_price_growth() 반환값.

    Returns:
        마크다운 형식의 AI 어드바이저 응답 문자열.
    """
    # TODO (김동하): init_vector_store()로 벡터스토어 로드
    # TODO (김동하): LangChain RetrievalQA 체인 구성 (부동산 규제 + 신한은행 FAQ 문서)
    # TODO (김동하): user_profile / target_apt / ml_prediction 기반 프롬프트 구성 후 체인 실행
    # STUB: RAG 완성 전까지 GPT 직접 호출로 임시 대체
    return _stub_gpt_response(user_profile, target_apt, ml_prediction)


def _stub_gpt_response(
    user_profile: dict,
    target_apt: dict,
    ml_prediction: dict,
) -> str:
    """STUB: RAG 완성 전 GPT 직접 호출 임시 구현.

    기존 app.py의 GPT-4o 호출 로직을 이관한 함수.
    get_loan_advice()가 RAG로 교체되면 이 함수는 삭제한다.

    Args:
        user_profile: get_loan_advice()의 user_profile과 동일.
        target_apt: get_loan_advice()의 target_apt와 동일.
        ml_prediction: get_loan_advice()의 ml_prediction과 동일.

    Returns:
        GPT-4o가 생성한 마크다운 리포트 문자열.
    """
    # TODO (김동하): app.py의 system_prompt / user_prompt 구성 로직 이관
    # TODO (김동하): OpenAI(api_key=...).chat.completions.create() 호출
    pass


def init_vector_store(docs_path: str | None = None):
    """RAG용 벡터스토어를 초기화한다.

    Args:
        docs_path: 문서 경로. None이면 config.VECTOR_STORE_DIR 사용.

    Returns:
        초기화된 벡터스토어 객체. STUB 상태에서는 None 반환.
    """
    # TODO (김동하): FAISS 또는 Chroma 벡터스토어 로드/생성
    # TODO (김동하): 부동산 규제 PDF + 신한은행 FAQ 문서 임베딩 및 인덱싱
    return None
