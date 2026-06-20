"""
LangChain RAG 기반 AI 어드바이저 모듈. (김동하 담당)

현재 STUB 상태 — _stub_gpt_response()가 GPT 직접 호출로 임시 동작한다.
김동하가 LangChain RAG 파이프라인 완성 후 get_loan_advice() 내부를 교체할 것.
함수 시그니처(입출력 타입)는 변경 금지.
"""

import os

from config import VECTOR_STORE_DIR

VECTORSTORE_PATH = str(VECTOR_STORE_DIR / "shinhan_faiss")


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
    retriever = init_vector_store()
    # TODO (김동하): LangChain RetrievalQA 체인 구성 (부동산 규제 + 신한은행 FAQ 문서)
    chain = _build_rag_chain(retriever)
    # TODO (김동하): user_profile / target_apt / ml_prediction 기반 프롬프트 구성 후 체인 실행
    query = _build_query(user_profile, target_apt, ml_prediction)
    return chain.invoke(query)


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
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings

    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings

    # TODO (김동하): FAISS 또는 Chroma 벡터스토어 로드/생성
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    path = docs_path or VECTORSTORE_PATH
    # TODO (김동하): 부동산 규제 PDF + 신한은행 FAQ 문서 임베딩 및 인덱싱
    vectorstore = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    return vectorstore.as_retriever(search_kwargs={"k": 5})


def _build_rag_chain(retriever):
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    prompt = ChatPromptTemplate.from_template("""
당신은 신한은행 주택담보대출 전문 AI 어드바이저입니다.
아래 [참고 문서]와 [고객 분석 데이터]를 종합하여 맞춤형 대출·투자 분석 리포트를 작성하세요.

[참고 문서]
{context}

[고객 분석 데이터]
{question}

[작성 지침]
- 마크다운 형식으로 작성하세요 (### 소제목, **강조** 활용).
- 아래 4개 섹션을 반드시 포함하세요:
  1. ### 대출 가능성 요약 — LTV/DSR 적합 여부, 자금 충족 여부
  2. ### 추천 대출 상품 — 가구 형태와 목적에 맞는 상품 추천 이유
  3. ### 투자 전망 — ML 예측 수치 기반 1/3/5년 시세 전망 해석
  4. ### 종합 의견 — 매수 결정 시 고려사항, 주의 사항
- 참고 문서에 없는 금리·한도 수치는 "영업점 또는 1599-8000 문의 권장"으로 안내하세요.
- 금리/한도는 시점에 따라 변동될 수 있음을 명시하세요.
- 한국어로, 전문적이면서 이해하기 쉽게 작성하세요.
""")

    def format_docs(docs):
        return "\n\n".join(
            f"[출처: {d.metadata.get('filename', '?')}]\n{d.page_content}"
            for d in docs
        )

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def _build_query(user_profile: dict, target_apt: dict, ml_prediction: dict) -> str:
    """user_profile / target_apt / ml_prediction을 RAG 체인용 쿼리 문자열로 변환한다."""

    def fmt(v):
        return f"{v:,}" if isinstance(v, int) else str(v)

    growth = ml_prediction.get("predicted_growth_pct", 0)

    return f"""
■ 고객 프로파일
- 가구 형태: {user_profile.get('household_type', '-')}
- 매매 목적: {user_profile.get('purpose', '-')}
- 부부합산 연소득: {fmt(user_profile.get('annual_income_man', 0))}만원
- 가용 자본금: {fmt(user_profile.get('available_cash_man', 0))}만원
- 기존 보유 대출: {fmt(user_profile.get('existing_loan_man', 0))}만원

■ 타겟 아파트
- 단지명: {target_apt.get('name', '-')}
- 주소: {target_apt.get('address', '-')}
- KB 매매시세: {fmt(target_apt.get('price_man', 0))}만원
- 면적: {target_apt.get('area', '-')}
- 세대수: {fmt(target_apt.get('units', 0))}세대
- 입주년월: {target_apt.get('completion', '-')}

■ ML 가격 예측
- 예측 상승률: {growth:+.1f}%
- 비고: {ml_prediction.get('note', '-')}

위 데이터를 바탕으로 이 고객에게 맞춤형 대출·투자 분석 리포트를 작성해주세요.
""".strip()
