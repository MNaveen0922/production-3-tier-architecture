import json
import logging

import boto3
import mysql.connector
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from secrets import load_config, get_db_password

app = FastAPI(title="Support Desk — Assignment Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("assignment-service")

# Load all config from SSM at startup
_cfg = load_config()


class AssignmentCreate(BaseModel):
    user_id: int
    ticket_id: int


# ==========================
# DATABASE CONNECTION
# ==========================
def get_db():
    return mysql.connector.connect(
        host=_cfg["DB_HOST"],
        user=_cfg["DB_USER"],
        password=get_db_password(),
        database=_cfg["DB_NAME"],
    )


# ==========================
# SQS HELPER
# ==========================
def send_to_sqs(message: dict):
    queue_url = _cfg.get("SQS_QUEUE_URL")
    if not queue_url:
        logger.info("SQS_QUEUE_URL not set — skipping SQS publish (local dev mode)")
        return
    try:
        sqs = boto3.client("sqs", region_name=_cfg["AWS_REGION"])
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
        logger.info(f"SQS message sent: {message.get('event_type')}")
    except ClientError as e:
        logger.error(f"SQS publish failed (non-critical): {e}")


# ==========================
# HEALTH CHECK
# ==========================
# ALB target group health check path: /assign/health
@app.get("/assign/health")
def health():
    return {"status": "healthy"}


# ==========================
# ASSIGN A TICKET TO AN AGENT
# ==========================
# After saving the record we additionally publish to SQS so a worker can
# send a confirmation email asynchronously.
@app.post("/assign", status_code=201)
def assign_ticket(body: AssignmentCreate):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Check ticket exists
        cursor.execute("SELECT id, title, priority FROM tickets WHERE id = %s", (body.ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            cursor.close(); conn.close()
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Check not already assigned to this agent
        cursor.execute(
            "SELECT id FROM assignment_records WHERE user_id = %s AND ticket_id = %s",
            (body.user_id, body.ticket_id),
        )
        if cursor.fetchone():
            cursor.close(); conn.close()
            raise HTTPException(status_code=409, detail="Already assigned")

        # ── Insert assignment record ──────────────────────────
        cursor.execute(
            "INSERT INTO assignment_records (user_id, ticket_id) VALUES (%s, %s)",
            (body.user_id, body.ticket_id),
        )
        conn.commit()

        # Fetch agent email for notification
        cursor.execute("SELECT name, email FROM users WHERE id = %s", (body.user_id,))
        user = cursor.fetchone()

        cursor.close(); conn.close()

        # ── Publish to SQS for async confirmation email ────────
        # Runs AFTER the DB commit so the response is never delayed.
        # The worker pod reads this message and sends the email.
        send_to_sqs({
            "event_type":      "ticket_assigned",
            "user_id":         body.user_id,
            "user_name":       user["name"] if user else "",
            "user_email":      user["email"] if user else "",
            "ticket_id":       body.ticket_id,
            "ticket_title":    ticket["title"],
            "ticket_priority": ticket["priority"],
        })

        return {"message": "Ticket assigned"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# MY ASSIGNED TICKETS
# ==========================
@app.get("/assign/mytickets/{user_id}")
def my_tickets(user_id: int):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT t.title, t.priority, t.status, ar.assigned_date
            FROM assignment_records ar
            JOIN tickets t ON ar.ticket_id = t.id
            WHERE ar.user_id = %s
            ORDER BY ar.assigned_date DESC
            """,
            (user_id,),
        )
        tickets = cursor.fetchall()
        cursor.close(); conn.close()
        return tickets

    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))
