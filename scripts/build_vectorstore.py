"""
RAG 벡터 DB 구축 스크립트
docs/ 폴더의 마크다운 파일들을 읽어서
청킹 → 임베딩 → FAISS 저장

사용법:
    pip install langchain langchain-openai langchain-community faiss-cpu tiktoken python-dotenv
    python scripts/build_vectorstore.py

전제조건:
    - .env에 OPENAI_API_KEY 설정
    - docs/shinhan_faq/*.md 파일 존재 (shinhan_scraper_v4.py 실행 후)
    - docs/regulations/*.md 파일 존재
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ─────────────────────────────────────────────────
DOCS_DIR        = Path("docs")
VECTORSTORE_DIR = Path("vectorstore")
VECTORSTORE_DIR.mkdir(exist_ok=True)

# 청킹 설정 (RAG 성능에 중요)
CHUNK_SIZE    = 500   # 토큰 기준 청크 크기
CHUNK_OVERLAP = 50    # 청크 간 겹침 (문맥 유지)

# 임베딩 모델
EMBED_MODEL = "text-embedding-3-small"  # 비용 저렴, 성능 충분


# ── 의존성 체크 ──────────────────────────────────────────
def check_dependencies():
    missing = []
    try: import langchain
    except ImportError: missing.append("langchain")
    try: import langchain_openai
    except ImportError: missing.append("langchain-openai")
    try: import langchain_text_splitters
    except ImportError: missing.append("langchain-text-splitters")
    try: import faiss
    except ImportError: missing.append("faiss-cpu")
    try: import tiktoken
    except ImportError: missing.append("tiktoken")

    if missing:
        print(f"❌ 누락된 패키지: {', '.join(missing)}")
        print(f"   pip install {' '.join(missing)}")
        exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY가 없습니다. .env 파일을 확인하세요.")
        exit(1)


# ── STEP 1: 문서 로딩 ────────────────────────────────────
def load_documents():
    from langchain_community.document_loaders import TextLoader
    from langchain_core.documents import Document

    print("\n📂 [STEP 1] 문서 로딩")
    print("=" * 50)

    docs = []
    md_files = list(DOCS_DIR.rglob("*.md"))

    if not md_files:
        print(f"  ❌ docs/ 폴더에 마크다운 파일이 없습니다.")
        print(f"  먼저 shinhan_scraper_v4.py를 실행하세요.")
        exit(1)

    for path in sorted(md_files):
        try:
            loader = TextLoader(str(path), encoding="utf-8")
            file_docs = loader.load()

            # 메타데이터 추가 (RAG 검색 결과에서 출처 표시용)
            for doc in file_docs:
                doc.metadata.update({
                    "source":   str(path),
                    "filename": path.name,
                    "category": path.parent.name,  # shinhan_faq or regulations
                })
            docs.extend(file_docs)
            print(f"  ✅ {path.relative_to(DOCS_DIR)} ({len(file_docs[0].page_content):,}자)")

        except Exception as e:
            print(f"  ⚠️  {path.name} 로딩 실패: {e}")

    print(f"\n  → 총 {len(docs)}개 파일, ", end="")
    total_chars = sum(len(d.page_content) for d in docs)
    print(f"{total_chars:,}자 로딩 완료")
    return docs


# ── STEP 2: 청킹 ─────────────────────────────────────────
def split_documents(docs):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    print(f"\n✂️  [STEP 2] 청킹 (chunk={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print("=" * 50)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n## ",    # H2 헤더 기준 우선 분할
            "\n### ",   # H3 헤더
            "\n\n",     # 단락
            "\n",       # 줄바꿈
            "。",        # 문장 끝
            " ",
            "",
        ],
        length_function=len,
    )

    chunks = splitter.split_documents(docs)

    print(f"  → {len(docs)}개 문서 → {len(chunks)}개 청크")
    print(f"  → 평균 청크 크기: {sum(len(c.page_content) for c in chunks) // len(chunks)}자")

    # 샘플 출력
    print(f"\n  📋 청크 샘플 (첫 번째):")
    print(f"  {'─'*40}")
    print(f"  {chunks[0].page_content[:200]}...")
    print(f"  출처: {chunks[0].metadata.get('filename')}")

    return chunks


# ── STEP 3: 임베딩 & FAISS 저장 ──────────────────────────
def build_vectorstore(chunks):
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS

    print(f"\n🔢 [STEP 3] 임베딩 & FAISS 저장")
    print("=" * 50)
    print(f"  모델: {EMBED_MODEL}")
    print(f"  청크 수: {len(chunks)}개")

    # 비용 예상 (text-embedding-3-small: $0.02/1M tokens)
    total_chars = sum(len(c.page_content) for c in chunks)
    est_tokens  = total_chars // 4  # 대략 4자 = 1토큰
    est_cost    = est_tokens / 1_000_000 * 0.02
    print(f"  예상 토큰: {est_tokens:,} (약 ${est_cost:.4f})")

    embeddings = OpenAIEmbeddings(
        model=EMBED_MODEL,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    print(f"\n  ⏳ 임베딩 생성 중... (잠시 대기)")
    start = time.time()

    # 배치 처리 (API 레이트 리밋 방지)
    BATCH_SIZE = 50
    all_chunks = chunks
    vectorstore = None

    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  배치 [{batch_num}/{total_batches}] {len(batch)}개 처리 중...")

        if vectorstore is None:
            vectorstore = FAISS.from_documents(batch, embeddings)
        else:
            vectorstore.add_documents(batch)

        if i + BATCH_SIZE < len(all_chunks):
            time.sleep(0.5)  # 레이트 리밋 방지

    elapsed = time.time() - start
    print(f"\n  ✅ 임베딩 완료 ({elapsed:.1f}초)")

    # 저장
    save_path = str(VECTORSTORE_DIR / "shinhan_faiss")
    vectorstore.save_local(save_path)
    print(f"  ✅ 저장 완료: {save_path}/")
    print(f"     - {save_path}/index.faiss")
    print(f"     - {save_path}/index.pkl")

    return vectorstore


# ── STEP 4: 검증 ─────────────────────────────────────────
def validate_vectorstore(vectorstore):
    from langchain_openai import OpenAIEmbeddings

    print(f"\n✔️  [STEP 4] 검증 테스트")
    print("=" * 50)

    TEST_QUERIES = [
        "신혼부부 주택담보대출 조건",
        "생애최초 주택구입 LTV 한도",
        "DSR 40% 계산 방법",
        "신한은행 주담대 우대금리",
        "디딤돌 대출 소득 기준",
    ]

    for query in TEST_QUERIES:
        results = vectorstore.similarity_search(query, k=2)
        print(f"\n  🔍 쿼리: '{query}'")
        for j, doc in enumerate(results, 1):
            preview = doc.page_content[:80].replace('\n', ' ')
            source  = doc.metadata.get('filename', '?')
            print(f"     [{j}] {source}: {preview}...")


# ── 메인 ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("🏗️  RAG 벡터 DB 구축 시작")
    print(f"📁 문서 경로: {DOCS_DIR.absolute()}")
    print(f"💾 저장 경로: {VECTORSTORE_DIR.absolute()}")

    check_dependencies()

    docs       = load_documents()
    chunks     = split_documents(docs)
    vectorstore = build_vectorstore(chunks)
    validate_vectorstore(vectorstore)

    print(f"\n🎉 완료! vectorstore/shinhan_faiss/ 에 저장됨")
    print(f"\n📌 다음 단계: src/rag/ingest.py 에서 로딩")
    print(f"""
# 사용 예시
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

embeddings   = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore  = FAISS.load_local("vectorstore/shinhan_faiss", embeddings,
                                allow_dangerous_deserialization=True)
retriever    = vectorstore.as_retriever(search_kwargs={{"k": 4}})
""")
