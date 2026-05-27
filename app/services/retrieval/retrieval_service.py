from ddgs import DDGS
import trafilatura

from app.schemas.research_schema import DocumentSchema


async def retrieve_web_documents(
    query: str,
    max_results:int
):

    documents: list[DocumentSchema] = []

    # perform web retrieval through DDGS
    with DDGS() as ddgs:

        results = ddgs.text(query, max_results=max_results)

        for result in results:

            url = result.get("href")

            if not url:
                continue

            # download and extract webpage content
            downloaded = trafilatura.fetch_url(url)

            content = trafilatura.extract(downloaded)

            # fallback to DDGS snippet if extraction fails
            if not content:
                content = result.get("body")

            # append response document
            documents.append(
                DocumentSchema(
                    title=result.get("title"),
                    url=url,
                    content=content,
                )
            )

    return documents