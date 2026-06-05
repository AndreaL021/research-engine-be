from app.config.llm_config import LLM_CONTEXT_CHUNKS
from app.schemas.research_schema import RetrievedChunkSchema


def build_answer_context(
    documents: list[RetrievedChunkSchema],
):
    context_documents = documents[:LLM_CONTEXT_CHUNKS]

    return "\n\n".join(
        [
            build_source_context(
                document=document,
            )
            for document in context_documents
        ]
    )


def build_source_context(
    document: RetrievedChunkSchema,
):
    metadata = build_source_metadata(document)
    source_number = document.source_number or 1

    return f"""[Source {source_number}]
Title: {document.title}
URL: {document.url}
{metadata}
Content:
{document.content}"""


def build_source_metadata(
    document: RetrievedChunkSchema,
):
    metadata = [
        f"Provider: {document.provider}",
        f"Source type: {document.source_type}",
        f"Content type: {document.content_type}",
        f"Reliability: {document.source_reliability}%",
        f"Retrieval score: {document.score:.3f}",
    ]

    optional_metadata = {
        "Chunk": document.chunk_index,
        "Author": document.author,
        "Published": document.published_at,
        "Search engine": document.search_engine,
        "Search category": document.search_category,
        "Categories": document.categories,
        "Tags": document.tags,
    }

    metadata.extend(
        [
            f"{key}: {value}"
            for key, value in optional_metadata.items()
            if value
        ]
    )

    return "\n".join(metadata)
