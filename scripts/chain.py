"""
신한은행 주담대 RAG 체인
사용법:
    python src/rag/chain.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

VECTORSTORE_PATH = str(Path("vector_store/shinhan_faiss"))


def load_retriever():
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.load_local(
        VECTORSTORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    return vectorstore.as_retriever(search_kwargs={"k": 4})


def build_chain(retriever):
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
당신은 신한은행 주택담보대출 전문 상담사입니다.
아래 참고 문서를 바탕으로 고객의 질문에 정확하고 친절하게 답변하세요.

[참고 문서]
{context}

[고객 질문]
{question}

[답변 지침]
- 참고 문서에 없는 내용은 "정확한 정보 확인을 위해 신한은행 영업점 또는 1599-8000으로 문의하세요"라고 안내하세요.
- 금리/한도는 시점에 따라 변동될 수 있음을 명시하세요.
- 답변은 한국어로, 간결하고 명확하게 작성하세요.
""")

    def format_docs(docs):
        return "\n\n".join(
            f"[출처: {d.metadata.get('filename', '?')}]\n{d.page_content}"
            for d in docs
        )

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


# ── 단일 질문 ─────────────────────────────────────────────
def ask(chain, question: str) -> str:
    print(f"\n{'='*50}")
    print(f"❓ {question}")
    print(f"{'='*50}")
    answer = chain.invoke(question)
    print(f"💬 {answer}")
    return answer


# ── 대화형 실행 ───────────────────────────────────────────
if __name__ == "__main__":
    print("🏦 신한은행 주담대 RAG 상담 시스템")
    print("벡터 DB 로딩 중...")

    retriever = load_retriever()
    chain     = build_chain(retriever)

    print("✅ 준비 완료! 질문을 입력하세요. (종료: q)\n")

    # 테스트 질문 자동 실행
    test_questions = [
        "신혼부부가 생애최초로 아파트 살 때 LTV 한도가 얼마야?",
        "신한 아파트론 금리가 어떻게 돼?",
        "DSR 40%면 연소득 6000만원일 때 월 상환 한도가 얼마야?",
    ]

    for q in test_questions:
        ask(chain, q)

    # 대화형 모드
    print(f"\n{'='*50}")
    print("💬 직접 질문해보세요")
    while True:
        user_input = input("\n질문: ").strip()
        if user_input.lower() in ("q", "quit", "exit", "종료"):
            print("종료합니다.")
            break
        if not user_input:
            continue
        ask(chain, user_input)
