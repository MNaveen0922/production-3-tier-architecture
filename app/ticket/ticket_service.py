import csv
import io
import json
import logging

import boto3
import mysql.connector
from botocore.exceptions import ClientError
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from secrets import load_config, get_db_password

app = FastAPI(title="Support Desk — Ticket Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket-service")

# Load all config from SSM at startup
_cfg = load_config()

logger.info("=" * 50)
logger.info(f"DB_HOST : {_cfg['DB_HOST']}")
logger.info(f"DB_NAME : {_cfg['DB_NAME']}")
logger.info(f"DB_USER : {_cfg['DB_USER']}")
logger.info("=" * 50)


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = "medium"


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
@app.get("/tickets/health")
def health():
    return {"status": "healthy"}


# ==========================
# GET ALL TICKETS
# ==========================
@app.get("/tickets")
def get_tickets():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tickets ORDER BY id DESC")
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"Returned {len(tickets)} tickets")
        return tickets
    except Exception as e:
        logger.error(f"get_tickets error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# GET SINGLE TICKET
# ==========================
@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        cursor.close()
        conn.close()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# CREATE A TICKET
# ==========================
# Notifies all subscribed agents via SQS -> worker -> SNS.
@app.post("/tickets", status_code=201)
def create_ticket(body: TicketCreate):
    try:
        if not body.title or not body.description:
            raise HTTPException(status_code=400, detail="title and description are required")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tickets (title, description, priority) VALUES (%s, %s, %s)",
            (body.title, body.description, body.priority),
        )
        conn.commit()
        ticket_id = cursor.lastrowid
        cursor.close()
        conn.close()

        # ── Notify agents via SQS → worker → SNS ──────────────
        send_to_sqs({
            "event_type":          "new_ticket_created",
            "ticket_id":           ticket_id,
            "ticket_title":        body.title,
            "ticket_priority":     body.priority,
        })

        logger.info(f"Ticket created: {body.title} ({body.priority})")
        return {"message": "Ticket created", "ticket_id": ticket_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"create_ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# BULK TICKET IMPORT (CSV)
# ==========================
# Accepts a CSV file upload. Each row is queued as a separate SQS message.
# The worker inserts rows into the DB one by one — this prevents long HTTP
# timeouts on large files and protects the DB from bulk insert spikes.
#
# CSV format (with header row):
#   title,description,priority
#   Printer jam,Printer on 2nd floor keeps jamming,low
#
@app.post("/tickets/import", status_code=202)
async def import_tickets(file: UploadFile = File(...)):
    try:
        content = (await file.read()).decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        queued = 0
        skipped = 0

        for row in reader:
            title       = (row.get("title") or "").strip()
            description = (row.get("description") or "").strip()
            priority    = (row.get("priority") or "medium").strip()

            if not title or not description:
                skipped += 1
                continue

            # Each ticket row goes into SQS as a separate message.
            # If the worker crashes mid-import, unprocessed messages
            # stay in the queue and get retried — no data loss.
            send_to_sqs({
                "event_type":      "bulk_ticket_import",
                "ticket_title":       title,
                "ticket_description": description,
                "ticket_priority":    priority,
            })
            queued += 1

        logger.info(f"Bulk import: {queued} queued, {skipped} skipped")
        return {
            "message":      f"{queued} tickets queued for import",
            "queued":       queued,
            "skipped_rows": skipped,
        }

    except Exception as e:
        logger.error(f"import_tickets error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
