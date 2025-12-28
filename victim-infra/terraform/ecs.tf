# ECS Cluster and Service for Victim Chatbot

# ECS Cluster
resource "aws_ecs_cluster" "chatbot" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-cluster"
  })
}

# CloudWatch Log Group for ECS
resource "aws_cloudwatch_log_group" "chatbot" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7

  tags = var.tags
}

# ECS Task Definition
resource "aws_ecs_task_definition" "chatbot" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "chatbot"
    image = "${aws_ecr_repository.chatbot.repository_url}:latest"

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "AWS_REGION"
        value = var.aws_region
      },
      {
        name  = "CODE_INTERPRETER_ID"
        value = aws_bedrockagentcore_code_interpreter.main.code_interpreter_id
      },
      {
        name  = "CODE_INTERPRETER_ARN"
        value = aws_bedrockagentcore_code_interpreter.main.code_interpreter_arn
      },
      {
        name  = "SENSITIVE_BUCKET"
        value = aws_s3_bucket.sensitive.id
      },
      {
        name  = "CUSTOMERS_TABLE"
        value = aws_dynamodb_table.customers.name
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.chatbot.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "chatbot"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = var.tags
}

# ECS Service
resource "aws_ecs_service" "chatbot" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.chatbot.id
  task_definition = aws_ecs_task_definition.chatbot.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.chatbot.arn
    container_name   = "chatbot"
    container_port   = 8000
  }

  # Allow external changes without Terraform plan difference
  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.http]

  tags = var.tags
}
