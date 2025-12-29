# Application Load Balancer for Victim Chatbot

resource "aws_lb" "chatbot" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = merge(var.tags, {
    Name = "${var.project_name}-alb"
  })
}

# Target Group for ECS Service
resource "aws_lb_target_group" "chatbot" {
  name        = "${var.project_name}-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 30
    interval            = 60
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-tg"
  })
}

# HTTP Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.chatbot.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.chatbot.arn
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-http-listener"
  })
}
