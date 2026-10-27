"""Course console product operations. Shared sandbox functions; no agent internals."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from app import templates
from sandbox import course

router = APIRouter()


def render(request, error=None):
    return templates.TemplateResponse(request, "home.html", {"page": "home", "error": error,
        "questions": [course.question(x["id"]) for x in course.records("question")],
        "documents": course.records("document"), "effects": course.effects(),
        "students": course.records("private_student"), "public_answers": course.records("public_answer")})


@router.get("/")
def home(request: Request):
    return render(request)


@router.post("/course/draft")
def draft(request: Request, question_id: str = Form(...), body: str = Form(...), sources: str = Form("")):
    try:
        ids = [s.strip() for s in sources.split(",") if s.strip()]
        for identifier in ids:
            doc = course.record("document", identifier)
            if not doc["active"] or doc["visibility"] != "public":
                raise ValueError("Choose active public sources.")
        course.manual_draft(question_id, body, ids)
    except ValueError as exc:
        return render(request, str(exc))
    return RedirectResponse("/", status_code=303)


@router.post("/course/send")
def send(request: Request, effect_id: str = Form(...), reviewed: str = Form("")):
    try:
        if reviewed != "yes":
            raise ValueError("Review the recipient, body, privacy and sources, then confirm review before sending.")
        course.send_pending(effect_id)
    except ValueError as exc:
        return render(request, str(exc))
    return RedirectResponse("/", status_code=303)


@router.post("/course/status")
def status(request: Request, effect_id: str = Form(...), status: str = Form(...), note: str = Form("")):
    try:
        course.update_status(effect_id, status, note)
    except ValueError as exc:
        return render(request, str(exc))
    return RedirectResponse("/", status_code=303)


@router.post("/course/flag")
def flag(request: Request, question_id: str = Form(...), reason: str = Form(...)):
    try:
        course.create_effect("flag", question_id, reason=reason, key=f"manual:flag:{question_id}")
    except ValueError as exc:
        return render(request, str(exc))
    return RedirectResponse("/", status_code=303)
