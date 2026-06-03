from app.config.config import LLM_CONTEXT_CHUNKS
from app.schemas.research_schema import DocumentSchema


def build_answer_context(
    documents: list[DocumentSchema],
):
    context_documents = documents[:LLM_CONTEXT_CHUNKS]

    return "\n\n".join(
        [
            build_source_context(
                source_number=index + 1,
                document=document,
            )
            for index, document in enumerate(context_documents)
        ]
    )


def build_source_context(
    source_number: int,
    document: DocumentSchema,
):
    metadata = build_source_metadata(document)

    return f"""[Source {source_number}]
Title: {document.title}
URL: {document.url}
{metadata}
Content:
{document.content}"""


def build_source_metadata(
    document: DocumentSchema,
):
    metadata = [
        f"Provider: {document.provider}",
        f"Source type: {document.source_type}",
        f"Content type: {document.content_type}",
        f"Reliability: {document.source_reliability}%",
        f"Retrieval score: {document.score:.3f}",
    ]

    optional_metadata = {
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
