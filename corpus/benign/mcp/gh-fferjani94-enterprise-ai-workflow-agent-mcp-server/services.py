import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise_ai_workflow_agent.db.models import (
    Account,
    KnowledgeDocument,
    Product,
    Ticket,
)

MAX_RESULTS = 20
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOPWORDS = {"a", "an", "and", "are", "for", "how", "in", "is", "of",
             "on", "or", "the", "to", "what", "with"}


def _limit(limit: int) -> int:
    if not 1 <= limit <= MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
    return limit


def _tokens(text: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(text.lower())
            if token not in STOPWORDS and len(token) > 1}


def search_accounts(db: Session, query: str, limit: int = 10) -> list[dict]:
    if not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > 200:
        raise ValueError("query must be at most 200 characters")
    rows = db.scalars(
        select(Account)
        .where(Account.name.ilike(f"%{query.strip()}%", escape="\\"))
        .order_by(Account.name)
        .limit(_limit(limit))
    ).all()
    return [{"id": a.id, "name": a.name, "industry": a.industry,
             "plan": a.plan, "status": a.status} for a in rows]


def get_account_tickets(db: Session, account_id: int, limit: int = 10) -> list[dict]:
    rows = db.scalars(
        select(Ticket)
        .where(Ticket.account_id == account_id)
        .order_by(Ticket.id)
        .limit(_limit(limit))
    ).all()
    return [{"id": t.id, "account_id": t.account_id, "product_id": t.product_id,
             "subject": t.subject, "status": t.status, "priority": t.priority}
            for t in rows]


def get_ticket_details(db: Session, ticket_id: int) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return {"found": False, "ticket_id": ticket_id}
    return {"found": True, "id": ticket.id, "account_id": ticket.account_id,
            "product_id": ticket.product_id, "subject": ticket.subject,
            "description": ticket.description, "status": ticket.status,
            "priority": ticket.priority}


def get_product_information(db: Session, product_id: int) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        return {"found": False, "product_id": product_id}
    return {"found": True, "id": product.id, "name": product.name,
            "version": product.version, "description": product.description}


def search_knowledge(
    db: Session, query: str, product_id: int | None = None, limit: int = 5
) -> list[dict]:
    if not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > 200:
        raise ValueError("query must be at most 200 characters")
    limit = _limit(limit)
    terms = _tokens(query)
    if not terms:
        return []
    statement = select(KnowledgeDocument).order_by(KnowledgeDocument.id)
    if product_id is not None:
        statement = statement.where(KnowledgeDocument.product_id == product_id)
    documents = db.scalars(statement).all()
    ranked = []
    for doc in documents:
        title_terms = _tokens(doc.title)
        body_terms = _tokens(doc.content)
        score = 3 * len(terms & title_terms) + len(terms & body_terms)
        if score:
            ranked.append((score, doc))
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    return [
        {"id": doc.id, "product_id": doc.product_id, "title": doc.title,
         "snippet": doc.content[:350], "source_url": doc.source_url,
         "score": score}
        for score, doc in ranked[:limit]
    ]
