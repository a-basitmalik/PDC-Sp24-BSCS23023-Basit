import threading
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel


STUDENT_ID = "BSCS23023"


class DocumentUpdate(BaseModel):
    content: str


class VersionedDocumentUpdate(DocumentUpdate):
    version: int


class Document(BaseModel):
    id: str
    content: str
    version: int


class DocumentStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._documents: dict[str, Document] = {}

    def reset(self) -> None:
        with self._lock:
            self._documents = {
                "shared-notes": Document(
                    id="shared-notes",
                    content="Initial StudySync notes",
                    version=1,
                )
            }

    def get(self, document_id: str) -> Document:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None:
                raise KeyError(document_id)
            return document.model_copy()

    def naive_update(self, document_id: str, content: str) -> Document:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None:
                raise KeyError(document_id)
            updated = Document(
                id=document.id,
                content=content,
                version=document.version + 1,
            )
            self._documents[document_id] = updated
            return updated.model_copy()

    def optimistic_update(
        self, document_id: str, content: str, expected_version: int
    ) -> Document:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None:
                raise KeyError(document_id)
            if document.version != expected_version:
                raise ValueError(document.version)

            updated = Document(
                id=document.id,
                content=content,
                version=document.version + 1,
            )
            self._documents[document_id] = updated
            return updated.model_copy()


store = DocumentStore()
store.reset()
app = FastAPI(title="StudySync Optimistic Locking Demo")


@app.middleware("http")
async def add_student_id_header(request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Student-ID"] = STUDENT_ID
    return response


def _get_document_or_404(document_id: str) -> Document:
    try:
        return store.get(document_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found") from None


@app.post("/reset", response_model=Document)
def reset_demo_state() -> Document:
    store.reset()
    return store.get("shared-notes")


@app.get("/documents/{document_id}", response_model=Document)
def get_document(document_id: str) -> Document:
    return _get_document_or_404(document_id)


@app.put("/naive/documents/{document_id}", response_model=Document)
def update_document_without_locking(
    document_id: str, payload: DocumentUpdate
) -> Document:
    try:
        return store.naive_update(document_id, payload.content)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found") from None


@app.put(
    "/documents/{document_id}",
    response_model=Document,
    status_code=status.HTTP_200_OK,
)
def update_document_with_optimistic_locking(
    document_id: str,
    payload: DocumentUpdate,
    if_match: Annotated[int | None, Header(alias="If-Match")] = None,
) -> Document:
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="If-Match header with the expected document version is required",
        )

    try:
        return store.optimistic_update(document_id, payload.content, if_match)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    except ValueError as exc:
        current_version = exc.args[0]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Document was modified by another user",
                "current_version": current_version,
            },
        ) from None
