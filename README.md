# Smart-Home-Camera

This system was implemented as an academic project in my Cloud Computation course. Both the parts combined contitutes a prototype that captures real-time video feed using Raspberry Pi, uploads it to S3 and detects the person in the video with an ML model hosted as a docker container in EC2 instance (IaaS mode), or AWS Lambda (Serverless mode) with custom load balancer spawning new instances (custom autoscaling using AWS SDK) as per load/traffic in an SQS queue. The results are stored in a Dynamo DB table.
