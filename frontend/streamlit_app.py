import os
from datetime import datetime

import requests
import streamlit as st

API_URL = os.getenv("HELPDESK_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="IT Helpdesk", layout="wide")
st.title("IT Helpdesk & Incident Management")


def api_request(method: str, path: str, **kwargs):
    response = requests.request(method, f"{API_URL}{path}", timeout=10, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else None


def format_sla_due(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%d %b %Y, %I:%M %p")


try:
    users = api_request("GET", "/users")
    categories = api_request("GET", "/categories")
    incidents = api_request("GET", "/incidents")
except requests.RequestException as exc:
    st.error(f"Cannot connect to the API at {API_URL}. Start FastAPI first. ({exc})")
    st.stop()

metrics = st.columns(5)
metrics[0].metric("Total", len(incidents))
metrics[1].metric("Open", sum(i["status"] == "open" for i in incidents))
metrics[2].metric("In progress", sum(i["status"] == "in_progress" for i in incidents))
metrics[3].metric("Resolved", sum(i["status"] == "resolved" for i in incidents))
metrics[4].metric("Overdue", sum(i["is_overdue"] for i in incidents))

st.subheader("Incidents")
status_filter = st.selectbox("Filter by status", ["all", "open", "in_progress", "resolved", "closed"])
if status_filter != "all":
    incidents = [i for i in incidents if i["status"] == status_filter]
st.dataframe(
    [
        {
            "ID": i["id"],
            "Title": i["title"],
            "Status": i["status"],
            "Impact": i["impact"] or "Legacy",
            "Urgency": i["urgency"] or "Legacy",
            "Priority": i["priority"],
            "SLA due": format_sla_due(i["sla_due_at"]),
            "Overdue": i["sla_status"],
        }
        for i in incidents
    ],
    use_container_width=True,
    hide_index=True,
)

with st.expander("Create incident"):
    with st.form("create_incident"):
        title = st.text_input("Title")
        description = st.text_area("Description")
        category = st.selectbox("Category", categories, format_func=lambda c: c["name"])
        impact = st.selectbox(
            "Impact", ["low", "medium", "high"], index=1, format_func=str.title
        )
        urgency = st.selectbox(
            "Urgency", ["low", "medium", "high"], index=1, format_func=str.title
        )
        calculated_priority = (
            "critical"
            if impact == "high" and urgency == "high"
            else "high"
            if impact == "high" or urgency == "high"
            else "medium"
            if impact == "medium" or urgency == "medium"
            else "low"
        )
        st.info(f"Calculated priority: {calculated_priority.title()}")
        requester = st.selectbox("Requester", users, format_func=lambda u: u["name"])
        assignee_options = [None] + [u for u in users if u["role"] in ("agent", "admin")]
        assignee = st.selectbox(
            "Assignee (optional)",
            assignee_options,
            format_func=lambda u: "Unassigned" if u is None else u["name"],
        )
        if st.form_submit_button("Create"):
            try:
                api_request(
                    "POST",
                    "/incidents",
                    json={
                        "title": title,
                        "description": description,
                        "impact": impact,
                        "urgency": urgency,
                        "requester_id": requester["id"],
                        "category_id": category["id"],
                        "assignee_id": assignee["id"] if assignee else None,
                    },
                )
                st.success("Incident created.")
                st.rerun()
            except requests.HTTPError as exc:
                st.error(exc.response.json().get("detail", "Request failed"))

with st.expander("Update incident status"):
    incident_ids = [i["id"] for i in api_request("GET", "/incidents")]
    if incident_ids:
        incident_id = st.selectbox("Incident", incident_ids)
        new_status = st.selectbox("New status", ["open", "in_progress", "resolved", "closed"])
        if st.button("Update status"):
            try:
                api_request(
                    "PATCH",
                    f"/incidents/{incident_id}/status",
                    json={"status": new_status},
                )
                st.success("Status updated.")
                st.rerun()
            except requests.HTTPError as exc:
                st.error(exc.response.json().get("detail", "Request failed"))
