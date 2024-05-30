output "s3_arn" {
  description = "ARN of the bucket"
  value       = aws_s3_bucket.clsec_bucket.arn
}

output "s3_name" {
  description = "Name (id) of the bucket"
  value       = aws_s3_bucket.clsec_bucket.id
}