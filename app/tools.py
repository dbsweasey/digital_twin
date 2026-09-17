from agents import function_tool, RunContextWrapper
import requests

from config import PUSHOVER_TOKEN, PUSHOVER_USER
from context import AppContext

def push_tool(message: str) -> str:
    payload = {"user": PUSHOVER_USER, "token": PUSHOVER_TOKEN, "message": message}
    result = requests.post("https://api.pushover.net/1/messages.json", data=payload).status_code
    return result

@function_tool
def record_user_details(email: str, name: str="Name not provided", notes: str="not provided") -> str:
    """ Records the user details when they ask to get in touch
    
    Args:
        email: The user's email address
        name: The user's name
        notes: Any additional notes the user wants to record alongside their contact info
    """
    result = push_tool(f"User wants to get in contact!\nEmail - {email}\nName - {name}\nNotes - {notes}")
    if result == 200:
        return f"{result} OK."
    return "FAILED."

@function_tool
def unknown_question(question: str):
    """ Always use this tool to record any question that could not be answered because you did not know
    
    Args:
        question: The question you were unable to answer
    """
    result = push_tool(f"Could not answer: {question}")
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
def get_project_details(wrapper: RunContextWrapper[AppContext], project_id: str) -> list[dict]:
    """ Retrieve full details for a specific project by its exact ID,
    obtained from search_projects.

    Args:
        project_id: EXACT project ID from search_project result
    """

    return wrapper.context.projects_by_id.get(project_id, {"error": f"No project found with id {project_id}"}) 