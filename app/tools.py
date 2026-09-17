from datetime import datetime

from agents import function_tool, RunContextWrapper
import smtplib
from email.message import EmailMessage

from config import TO_EMAIL_ADDRESS, FROM_EMAIL_ADDRESS, EMAIL_SMTP_SERVER, EMAIL_APP_PASSWORD
from context import AppContext

def email_tool(message: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    _send_email(f"[Digital Twin] New Message - {now}", message, f"<p>{message}</p>")
    return 200

def _send_email(subject, text_body, html_body):
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL_ADDRESS
    msg["To"] = TO_EMAIL_ADDRESS
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    print(f"Sending email to {TO_EMAIL_ADDRESS} with subject '{subject}' and body '{text_body}'")

    with smtplib.SMTP(EMAIL_SMTP_SERVER, 587) as server:
        server.starttls()
        server.login(FROM_EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)

@function_tool
def record_user_details(email: str, name: str="Name not provided", notes: str="not provided") -> str:
    """ Records the user details when they ask to get in touch. Only use when they actually provide at least an email.
    
    Args:
        email: The user's email address
        name: The user's name
        notes: Any additional notes the user wants to record alongside their contact info
    """
    result = email_tool(f"User wants to get in contact!\nEmail - {email}\nName - {name}\nNotes - {notes}")
    if result == 200:
        return f"{result} OK."
    return "FAILED."

@function_tool
def unknown_question(question: str):
    """ Always use this tool to record any question that could not be answered because you did not know
    
    Args:
        question: The question you were unable to answer
    """
    result = email_tool(f"Could not answer: {question}")
    if result == 200:
        return f"{result} OK."
    return "FAILED."

@function_tool
def search_projects(wrapper: RunContextWrapper[AppContext], query: str) -> list[dict]:
    """ Search across all projects by keyword, technology, or topic.
    ALWAYS call this first if you do not know the exact project ID.

    Args:
        query: Free-text search (stocks, dashboard, API)
    """
    projects = wrapper.context.projects
    scored = []
    for p in projects:
        haystack = " ".join([p["name"], p["summary"], *p["aliases"], *p["stack"]]).lower()
        score = sum(1 for w in query.lower().split() if w in haystack)
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [{"id": p["id"], "name": p["name"], "summary": p["summary"]} for _, p in scored][:3]

@function_tool
def list_projects_by_category(wrapper: RunContextWrapper[AppContext], category: str) -> list[dict]:
    """ List all projects in a given category. ALWAYS use this (not search_projects) when the user
    asks broadly about "personal projects", "work projects", or "school/class projects" rather than
    naming a specific technology or project.

    Args:
        category: One of "personal", "work", or "school"
    """
    projects = wrapper.context.projects
    matches = [p for p in projects if p.get("category") == category]
    return [{"id": p["id"], "name": p["name"], "summary": p["summary"]} for p in matches]

@function_tool
def get_project_details(wrapper: RunContextWrapper[AppContext], project_id: str) -> list[dict]:
    """ Retrieve full details for a specific project by its exact ID,
    obtained from search_projects.

    Args:
        project_id: EXACT project ID from search_project result
    """

    return wrapper.context.projects_by_id.get(project_id, {"error": f"No project found with id {project_id}"}) 