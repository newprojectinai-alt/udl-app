# UDL Learn Deployment Guide

This guide deploys the three services as:

```text
Vercel Vite frontend
        |
        v
AWS ECS Fargate FastAPI backend ----> Supabase PostgreSQL
        |                       \
        |                        -> private Amazon S3 media bucket
        v
RunPod CogVideoX GPU Pod
```

The frontend never receives the RunPod token, AI keys, Supabase service-role key, or AWS credentials.

## Important Security Status

The current frontend uses local demo role switching rather than real authentication. The deployment below is suitable for an MVP or controlled demo, but the backend endpoints are not protected by user login. Add Supabase Auth/JWT verification before opening teacher/admin functionality to untrusted public users.

## 1. Prepare Supabase

1. Create a Supabase project.
2. Open the SQL editor.
3. Run `backend/db/schema.sql`.
4. Keep the project URL and service-role key for the AWS backend.
5. Never add the service-role key to Vercel.

## 2. Deploy CogVideoX to RunPod

### Build and publish the image

Replace `YOUR_DOCKERHUB_USER`:

```bash
docker login
docker build -t YOUR_DOCKERHUB_USER/udl-cogvideo:latest ./cogvideo-server
docker push YOUR_DOCKERHUB_USER/udl-cogvideo:latest
```

### Create the RunPod template

1. Create a RunPod Pod template using the published image.
2. Choose an NVIDIA GPU with at least 24 GB VRAM. An RTX 4090, L40S, A5000, A6000, or A100 is appropriate.
3. Add a network volume of at least 80 GB. Mount it at `/workspace` so the Hugging Face model cache survives restarts.
4. Expose HTTP port `8000`.
5. Keep the image's default start command.
6. Add the environment variables from the RunPod table below.
7. Deploy the Pod and wait for the model to download and `/health` to become available.

RunPod's HTTP URL format is:

```text
https://POD_ID-8000.proxy.runpod.net
```

Health check:

```text
https://POD_ID-8000.proxy.runpod.net/health
```

The backend must use the asynchronous endpoint:

```text
https://POD_ID-8000.proxy.runpod.net/jobs
```

RunPod's HTTP proxy has a 100-second connection limit, so the code submits a job, polls its status, and downloads the completed result instead of holding one generation request open.

### RunPod environment variables

| Variable | Required | Example |
| --- | --- | --- |
| `VIDEO_API_TOKEN` | Yes | A long random secret |
| `COGVIDEO_MODEL_ID` | Yes | `zai-org/CogVideoX-5b` |
| `COGVIDEO_NUM_FRAMES` | No | `49` |
| `COGVIDEO_NUM_STEPS` | No | `35` |
| `COGVIDEO_GUIDANCE_SCALE` | No | `6.0` |
| `OUTPUT_DIR` | Yes | `/workspace/outputs` |
| `HF_TOKEN` | Sometimes | Required if the selected model/account needs Hugging Face authentication |

## 3. Deploy the Backend to AWS ECS Fargate

AWS App Runner is no longer open to new customers, so this guide uses ECS Fargate. The backend container is stored in Amazon ECR and exposed through an Application Load Balancer.

Choose one AWS region and use it consistently. The examples use `eu-central-1`.

### Create a private S3 bucket

1. Create an S3 bucket, for example `your-unique-udl-media`.
2. Keep **Block all public access** enabled.
3. Use the same region as ECS.
4. The backend generates temporary presigned download URLs; the bucket does not need to be public.

### Create the ECS task role

1. Replace `YOUR_S3_BUCKET` in `deployment/aws/ecs-task-s3-policy.json`.
2. Create an IAM policy from that JSON.
3. Create an IAM role using the **Elastic Container Service Task** use case.
4. Attach the policy to the role.
5. Use this role as the task role in the ECS task definition.

Do not set `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in the container. Boto3 obtains temporary credentials from the ECS task role.

### Build and push the backend image to ECR

Set these shell values:

```bash
AWS_REGION=eu-central-1
AWS_ACCOUNT_ID=123456789012
ECR_REPOSITORY=udl-backend
```

Create the repository and authenticate Docker:

```bash
aws ecr create-repository --repository-name "$ECR_REPOSITORY" --region "$AWS_REGION"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

Build and push:

```bash
docker build -t "$ECR_REPOSITORY:latest" ./backend
docker tag "$ECR_REPOSITORY:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
```

### Create the ECS service

1. Create an ECS cluster using AWS Fargate.
2. Create a Fargate task definition:
   - Operating system: Linux
   - Architecture: `X86_64`
   - CPU: 2 vCPU
   - Memory: 4 GB
   - Image: the ECR image URI
   - Container port: `5000`
   - Task role: the S3 role created above
   - Task execution role: `ecsTaskExecutionRole`
   - Send logs to CloudWatch Logs
3. Add the AWS backend environment variables from the table below. Store secret values in AWS Secrets Manager and reference them from the task definition's **Secrets** section.
4. Create an ECS service with desired count `1`.
5. Enable **Assign public IP** unless the task is in private subnets with a NAT gateway. The backend needs outbound HTTPS access to Supabase, Gemini/OpenAI, and RunPod.
6. Attach an internet-facing Application Load Balancer:
   - Listener: HTTPS `443`
   - Target container port: `5000`
   - Health check path: `/api/health`
   - Healthy response code: `200`
7. Configure security groups:
   - ALB security group: inbound `443` from the internet
   - ECS security group: inbound `5000` only from the ALB security group
8. Create an ACM certificate and DNS record for a backend domain such as `api.example.com`, then attach the certificate to the HTTPS listener.

Vercel is HTTPS, so the browser-facing AWS API must also be HTTPS. Do not use a plain `http://` ALB address in `VITE_API_BASE_URL`.

### AWS backend environment variables

| Variable | Required | Example |
| --- | --- | --- |
| `PORT` | Yes | `5000` |
| `FRONTEND_URL` | Yes | `https://your-app.vercel.app` |
| `FRONTEND_URLS` | Yes | `https://your-app.vercel.app,https://www.example.com` |
| `CORS_ORIGIN_REGEX` | No | Leave empty for production; use only for tightly scoped preview domains |
| `APP_URL` | Yes | `https://your-app.vercel.app` |
| `AI_PROVIDER` | Yes | `gemini` |
| `GEMINI_API_KEY` | If using Gemini | Store in Secrets Manager |
| `GEMINI_MODEL` | If using Gemini | `gemini-2.5-flash` |
| `OPENAI_API_KEY` | If using OpenAI | Store in Secrets Manager |
| `OPENAI_MODEL` | If using OpenAI | `gpt-4o-mini` |
| `OPENROUTER_API_KEY` | If using OpenRouter | Store in Secrets Manager |
| `OPENROUTER_MODEL` | If using OpenRouter | Provider model ID |
| `SUPABASE_URL` | Yes | `https://PROJECT.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Store in Secrets Manager |
| `VIDEO_API_ENDPOINT` | Yes | `https://POD_ID-8000.proxy.runpod.net/jobs` |
| `VIDEO_API_TOKEN` | Yes | Same secret as RunPod; store in Secrets Manager |
| `VIDEO_API_MODE` | Yes | `async` |
| `VIDEO_API_POLL_SECONDS` | Yes | `5` |
| `VIDEO_API_REQUEST_TIMEOUT_SECONDS` | Yes | `90` |
| `HF_VIDEO_TIMEOUT_SECONDS` | Yes | `1800` |
| `HF_VIDEO_NUM_FRAMES` | No | `49` |
| `HF_VIDEO_GUIDANCE_SCALE` | No | `6.0` |
| `AWS_REGION` | Yes | `eu-central-1` |
| `AWS_S3_BUCKET` | Yes | `your-unique-udl-media` |
| `AWS_S3_PREFIX` | Yes | `udl-learn` |
| `AWS_S3_PRESIGNED_TTL_SECONDS` | No | `3600` |
| `SKIP_TTS` | Recommended initially | `true` |

The backend uses its temporary filesystem only while processing. Uploaded textbooks, generated audio, and rendered MP4 files are stored in private S3.

## 4. Deploy the Frontend to Vercel

1. Push the repository to GitHub, GitLab, or Bitbucket.
2. Import the repository in Vercel.
3. Keep the project root as the repository root.
4. Vercel should detect Vite:
   - Install command: `npm install`
   - Build command: `npm run build`
   - Output directory: `dist`
5. Add the two Vercel variables below to Production and Preview as needed.
6. Deploy.
7. After Vercel gives you the final domain, update `FRONTEND_URL`, `FRONTEND_URLS`, and `APP_URL` in ECS and force a new ECS deployment.

### Vercel environment variables

| Variable | Required | Example |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Yes | `https://api.example.com` |
| `VITE_USE_BACKEND` | Yes | `true` |

Only variables prefixed with `VITE_` are exposed to the frontend bundle. Never put AI keys, the Supabase service-role key, AWS credentials, or `VIDEO_API_TOKEN` in Vercel.

`vercel.json` includes the SPA rewrite required for React Router deep links.

## 5. Smoke Tests

### RunPod

```bash
curl "https://POD_ID-8000.proxy.runpod.net/health"
```

Submit a small job:

```bash
curl -X POST "https://POD_ID-8000.proxy.runpod.net/jobs" \
  -H "Authorization: Bearer YOUR_VIDEO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs":"A short educational animation of the water cycle","parameters":{"num_frames":25,"num_inference_steps":20}}'
```

Use the returned `status_url` until the job is completed.

### AWS

```bash
curl "https://api.example.com/api/health"
```

Expected fields include:

```json
{
  "ok": true,
  "storage": "s3",
  "video_api_mode": "async"
}
```

### Vercel

1. Open the landing page.
2. Refresh a nested route such as `/student`.
3. Generate or open a lesson.
4. Create a video storyboard and start rendering.
5. Confirm the UI polls until the S3-backed video appears.

## 6. Operational Notes

- A RunPod Pod must remain running for the API URL to work. Stopping it stops generation.
- Keep RunPod's `/workspace` on persistent storage to avoid downloading the model after every restart.
- ECS FastAPI background tasks are acceptable for an MVP, but a task restart can interrupt an active render. For production reliability, move render work to SQS plus a dedicated ECS worker.
- Set CloudWatch log retention and AWS billing alarms.
- Restrict CORS to exact Vercel/custom domains.
- Rotate `VIDEO_API_TOKEN`, AI keys, and the Supabase service-role key if they are ever exposed.

## Official References

- Vercel Vite deployment and SPA rewrites: <https://vercel.com/docs/frameworks/frontend/vite>
- AWS ECS Fargate getting started: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html>
- AWS ECS task IAM roles: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html>
- Amazon ECR image workflow: <https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html>
- Amazon S3 presigned URLs: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html>
- RunPod exposed HTTP ports: <https://docs.runpod.io/pods/configuration/expose-ports>
