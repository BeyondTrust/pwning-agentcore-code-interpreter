# DynamoDB tables with sensitive data for VDP demonstration

resource "aws_dynamodb_table" "sensitive_customer_data" {
  name           = "CustomerRecords"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  tags = merge(var.tags, {
    Name           = "Customer Records"
    Classification = "Confidential"
    Purpose        = "VDP Demonstration"
  })
}

# Add some sample sensitive data
resource "aws_dynamodb_table_item" "customer_1" {
  table_name = aws_dynamodb_table.sensitive_customer_data.name
  hash_key   = aws_dynamodb_table.sensitive_customer_data.hash_key

  item = jsonencode({
    customer_id = { S = "CUST-1001" }
    name        = { S = "Alice Johnson" }
    email       = { S = "alice.johnson@example.com" }
    ssn         = { S = "123-45-6789" }
    credit_card = { S = "4532-1234-5678-9012" }
    balance     = { N = "15420.50" }
    vip_status  = { BOOL = true }
  })

  lifecycle {
    ignore_changes = [item]
  }
}

resource "aws_dynamodb_table_item" "customer_2" {
  table_name = aws_dynamodb_table.sensitive_customer_data.name
  hash_key   = aws_dynamodb_table.sensitive_customer_data.hash_key

  item = jsonencode({
    customer_id = { S = "CUST-1002" }
    name        = { S = "Robert Martinez" }
    email       = { S = "robert.m@example.com" }
    ssn         = { S = "987-65-4321" }
    credit_card = { S = "5555-4444-3333-2222" }
    balance     = { N = "8750.25" }
    vip_status  = { BOOL = false }
  })

  lifecycle {
    ignore_changes = [item]
  }
}

resource "aws_dynamodb_table_item" "customer_3" {
  table_name = aws_dynamodb_table.sensitive_customer_data.name
  hash_key   = aws_dynamodb_table.sensitive_customer_data.hash_key

  item = jsonencode({
    customer_id = { S = "CUST-1003" }
    name        = { S = "Sarah Chen" }
    email       = { S = "sarah.chen@example.com" }
    ssn         = { S = "456-78-9012" }
    credit_card = { S = "4111-1111-1111-1111" }
    balance     = { N = "23890.00" }
    vip_status  = { BOOL = true }
  })

  lifecycle {
    ignore_changes = [item]
  }
}

# Additional table for demonstrating multiple table access
resource "aws_dynamodb_table" "payment_transactions" {
  name           = "PaymentTransactions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  tags = merge(var.tags, {
    Name           = "Payment Transactions"
    Classification = "Financial"
    Purpose        = "VDP Demonstration"
  })
}

resource "aws_dynamodb_table_item" "transaction_1" {
  table_name = aws_dynamodb_table.payment_transactions.name
  hash_key   = aws_dynamodb_table.payment_transactions.hash_key

  item = jsonencode({
    transaction_id = { S = "TXN-20241019-001" }
    customer_id    = { S = "CUST-1001" }
    amount         = { N = "1250.00" }
    status         = { S = "completed" }
    card_last4     = { S = "9012" }
    timestamp      = { S = "2024-10-19T12:34:56Z" }
  })

  lifecycle {
    ignore_changes = [item]
  }
}

resource "aws_dynamodb_table_item" "transaction_2" {
  table_name = aws_dynamodb_table.payment_transactions.name
  hash_key   = aws_dynamodb_table.payment_transactions.hash_key

  item = jsonencode({
    transaction_id = { S = "TXN-20241019-002" }
    customer_id    = { S = "CUST-1002" }
    amount         = { N = "750.50" }
    status         = { S = "completed" }
    card_last4     = { S = "2222" }
    timestamp      = { S = "2024-10-19T14:22:10Z" }
  })

  lifecycle {
    ignore_changes = [item]
  }
}

