from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.language_models import BaseLanguageModel


def _format_docs(docs: list) -> str:
    return "\n\n".join(getattr(d, "page_content", str(d)) for d in docs)


def build_rag_chain(llm: BaseLanguageModel, retriever):
    """retriever: LangChain BaseRetriever with .invoke(query) -> Documents."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Use only the following context to answer. If the answer is not in the context, say you do not know.\n\n{context}",
            ),
            ("human", "{question}"),
        ]
    )

    chain = (
        RunnablePassthrough.assign(
            context=lambda x: _format_docs(retriever.invoke(x["question"]))
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain