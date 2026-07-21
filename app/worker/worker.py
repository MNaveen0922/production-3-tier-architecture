"""
worker.py — SQS Message Worker

This service runs as a separate pod in EKS alongside the FastAPI services.
It continuously polls the SQS queue and processes messages based on event_type.

Three event types handled:
  1. ticket_assigned      → sends assignment confirmation email via SNS
  2. new_ticket_created   → notifies all subscribed agents via SNS
  3. bulk_ticket_import   → inserts a single ticket into RDS

Why a separate worker instead of processing inside the API?
  - The API handles HTTP requests — it should respond fast
  - Email sending, DB inserts, and retries happen here, not in the API
  - If the worker crashes, SQS keeps messages safe until it restarts
  - DLQ catches messages that fail repeatedly for investigation
"""

import json
import logging
import time

import boto3
import mysql.connector
from botocore.exceptions import ClientError
from secrets import load_config, get_db_password

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("worker")

# Load all config from SSM at startup — blocks until fetched
_cfg          = load_config()
REGION        = _cfg["AWS_REGION"]
SQS_QUEUE_URL = _cfg["SQS_QUEUE_URL"]
SNS_TOPIC_ARN = _cfg["SNS_TOPIC_ARN"]

sqs = boto3.client("sqs", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)


# ── Database connection ───────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host=_cfg["DB_HOST"],
        user=_cfg["DB_USER"],
        password=get_db_password(),
        database=_cfg["DB_NAME"]
    )


# ── Event handlers ────────────────────────────────────────────

def handle_ticket_assigned(data: dict):
    """
    Sends a ticket-assignment confirmation email to the agent via SNS.
    SNS delivers it to any email subscribed on the alerts topic.
    """
    user_name      = data.get("user_name", "Agent")
    user_email     = data.get("user_email", "")
    ticket_title   = data.get("ticket_title", "")
    ticket_priority = data.get("ticket_priority", "")

    message = (
        f"Hello {user_name},\n\n"
        f"You have been assigned a support ticket:\n"
        f"  Title:    {ticket_title}\n"
        f"  Priority: {ticket_priority}\n\n"
        f"Please review it in the Support Desk portal.\n"
        f"— Support Desk Team"
    )

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"Ticket Assigned: {ticket_title}",
        Message=message
    )
    logger.info(f"Assignment confirmation sent for {user_email} — ticket: {ticket_title}")


def handle_new_ticket_created(data: dict):
    """
    Notifies all SNS subscribers (on-call agents) that a new ticket was raised.
    """
    ticket_title    = data.get("ticket_title", "")
    ticket_priority = data.get("ticket_priority", "")

    message = (
        f"A new support ticket has been created!\n\n"
        f"  Title:    {ticket_title}\n"
        f"  Priority: {ticket_priority}\n\n"
        f"Log in to the Support Desk portal to triage it."
    )

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"New Ticket: {ticket_title}",
        Message=message
    )
    logger.info(f"New ticket notification sent: {ticket_title}")


def handle_bulk_ticket_import(data: dict):
    """
    Inserts a single ticket into the RDS database.
    Each CSV row arrives as a separate SQS message so:
      - Large imports don't time out the API
      - Failed rows go to DLQ for investigation
      - DB is never hammered with bulk inserts
    """
    title       = data.get("ticket_title", "").strip()
    description = data.get("ticket_description", "").strip()
    priority    = data.get("ticket_priority", "medium").strip() or "medium"

    if not title or not description:
        logger.warning(f"Skipping invalid bulk import row: {data}")
        return

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tickets (title, description, priority) VALUES (%s, %s, %s)",
        (title, description, priority)
    )
    conn.commit()
    cursor.close(); conn.close()
    logger.info(f"Bulk import — inserted ticket: {title}")


# ── Message dispatcher ────────────────────────────────────────

def process_message(message: dict):
    """
    Routes each SQS message to the correct handler based on event_type.
    Unrecognised event types are logged and skipped (not retried).
    """
    event_type = message.get("event_type")

    if event_type == "ticket_assigned":
        handle_ticket_assigned(message)

    elif event_type == "new_ticket_created":
        handle_new_ticket_created(message)

    elif event_type == "bulk_ticket_import":
        handle_bulk_ticket_import(message)

    else:
        logger.warning(f"Unknown event_type: {event_type} — skipping")


# ── Main polling loop ─────────────────────────────────────────

def run():
    """
    Polls SQS continuously.
    Long polling (WaitTimeSeconds=20) reduces empty API calls and cost.
    Each message is deleted only after successful processing.
    If processing raises an exception, the message is NOT deleted —
    SQS makes it visible again after visibility_timeout and retries it.
    After max_receive_count failures it moves to the Dead Letter Queue (DLQ).
    """
    logger.info(f"Worker started. Polling queue: {SQS_QUEUE_URL}")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl            = SQS_QUEUE_URL,
                MaxNumberOfMessages = 10,     # process up to 10 at once
                WaitTimeSeconds     = 20,     # long poll — waits 20s for messages
                VisibilityTimeout   = 60      # worker has 60s to process each message
            )

            messages = response.get("Messages", [])

            if not messages:
                logger.debug("No messages — waiting...")
                continue

            for msg in messages:
                receipt_handle = msg["ReceiptHandle"]
                try:
                    body = json.loads(msg["Body"])
                    logger.info(f"Processing: {body.get('event_type')} — id: {msg['MessageId']}")

                    process_message(body)

                    # Delete message only after successful processing
                    sqs.delete_message(
                        QueueUrl      = SQS_QUEUE_URL,
                        ReceiptHandle = receipt_handle
                    )
                    logger.info(f"Message processed and deleted: {msg['MessageId']}")

                except Exception as e:
                    # Don't delete — SQS will retry after visibility timeout
                    logger.error(f"Failed to process message {msg['MessageId']}: {e}")

        except ClientError as e:
            logger.error(f"SQS receive error: {e}")
            time.sleep(5)   # brief pause before retrying on AWS errors

        except Exception as e:
            logger.error(f"Unexpected worker error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run()
