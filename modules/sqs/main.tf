resource "aws_sqs_queue" "orders_dlq" {
  name = "${var.project_name}-${var.environment}-orders-dlq"


  message_retention_seconds = var.message_retention_seconds

  tags = {
    Name = "${var.project_name}-${var.environment}-orders-dlq"
  }
}


resource "aws_sqs_queue" "orders" {
  name = "${var.project_name}-${var.environment}-orders-queue"

  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.orders_dlq.arn
    maxReceiveCount      = var.max_receive_count
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-orders-queue"
  }
}


resource "aws_sqs_queue_redrive_allow_policy" "orders_dlq" {
  queue_url = aws_sqs_queue.orders_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.orders.arn]
  })
}

