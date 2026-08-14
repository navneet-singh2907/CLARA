# CLARA AWS Evidence Deployment

This deployment is designed to prove that CLARA can run as a multi-container
application on AWS. Vercel remains the permanent public demo. Terminate the AWS
environment after capturing the resume screenshots and video.

## Architecture

```text
Elastic Beanstalk URL
        |
      Nginx :80
      /       \
Next.js     /api/* -> FastAPI
  :3000                 :8000
                          |
                LangGraph + LLM provider
```

Nginx gives the deployment one public origin. The frontend uses `/api`, so API
keys remain server-side and browser requests do not point to localhost. SSE
buffering is disabled so the live LangGraph timeline can stream through Nginx.

## 1. Test the AWS topology locally

Elastic Beanstalk creates `.env` from the environment properties configured in
AWS. For the local test, the existing ignored `.env` file provides those values.

```powershell
docker compose -f docker-compose.aws.yml up --build
```

Open:

- CLARA: `http://localhost`
- API health: `http://localhost/health`
- API readiness: `http://localhost/readiness`

Run one review and confirm that the live agent timeline completes. Stop the
stack afterward:

```powershell
docker compose -f docker-compose.aws.yml down
```

## 2. Commit and build the deployment bundle

Elastic Beanstalk auto-detects a root file named `docker-compose.yml`. The bundle
script uses committed files only, replaces the local Compose file with the AWS
Compose file inside the ZIP, and refuses to package `.env`.

```powershell
.\scripts\build_aws_bundle.ps1
```

Expected artifact:

```text
tmp\clara-aws-elastic-beanstalk.zip
```

## 3. Create the Elastic Beanstalk environment

In the AWS Console:

1. Open **Elastic Beanstalk** and choose **Create application**.
2. Application name: `clara-loan-review`.
3. Environment tier: **Web server environment**.
4. Platform: **Docker running on 64bit Amazon Linux 2023**.
5. Application code: upload `tmp\clara-aws-elastic-beanstalk.zip`.
6. Configuration preset: **Single instance**.
7. Use a temporary `t3.medium` instance for enough memory to build the Python
   and Next.js images. Terminate it after evidence capture.

Elastic Beanstalk detects the bundled `docker-compose.yml` and starts the API,
web, and proxy containers on one EC2 instance.

## 4. Configure environment properties

Open the environment, then **Configuration > Updates, monitoring, and logging >
Environment properties**. Set the values required by the current CLARA setup:

```text
USE_LLM_AGENTS=true
LLM_PROVIDER=nebius
NEBIUS_API_KEY=<secret>
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
OPENAI_MODEL=<available Nebius model ID>
LLM_TEMPERATURE=0.2
PRIMARY_JUDGE_MODEL=<available primary judge model ID>
SECONDARY_JUDGE_MODEL=<available secondary judge model ID>
JUDGE_TEMPERATURE=0.2
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<secret>
LANGSMITH_PROJECT=CLARA-AWS
```

Do not add `NEXT_PUBLIC_API_BASE_URL`; the AWS image is intentionally compiled
to use same-origin `/api` routing. Do not upload the local `.env` file.

For stronger secret handling, Elastic Beanstalk platform releases from March
26, 2025 onward can reference AWS Secrets Manager or Systems Manager Parameter
Store values from environment properties.

## 5. Verify the deployment

Wait for the environment health to become **Green / Ok**, then verify:

```text
http://<environment-domain>/health
http://<environment-domain>/readiness
http://<environment-domain>/
```

Run this evidence sequence:

1. Select an adversarial or known-failure case.
2. Start the review pipeline.
3. Show term extraction, schema validation, parallel compliance and risk
   scoring, and synthesis in the live timeline.
4. Show the final decision packet.
5. Download the PDF packet.
6. Open LangSmith and show the corresponding trace.

## 6. Capture resume evidence

Capture screenshots of:

- Elastic Beanstalk environment showing healthy status.
- The AWS environment URL running CLARA.
- `/readiness` showing live LLM and LangSmith configuration.
- A completed live agent timeline.
- The final review decision and PDF packet.
- The Elastic Beanstalk event or deployment log showing successful deployment.

Suggested resume wording:

> Containerized CLARA's Next.js and FastAPI services with Docker and deployed
> the multi-service application to AWS Elastic Beanstalk behind an
> SSE-compatible Nginx gateway, while retaining Vercel as the public demo.

## 7. Terminate resources

After recording:

1. In Elastic Beanstalk, choose **Actions > Terminate environment**.
2. Confirm that the EC2 instance and environment are terminated.
3. Check EC2 Load Balancers, ECR, S3, and CloudWatch for resources or retained
   artifacts that may continue to incur charges.
4. Keep the screenshots and video; continue using the Vercel URL publicly.

## Troubleshooting

### Environment is red during deployment

Open **Logs > Request logs > Last 100 lines**. The most common causes are Docker
build memory limits, a missing environment property, or a port-80 conflict.

### UI opens but API calls fail

Confirm `/health` works and inspect the browser request URL. AWS requests must
use `/api/...`, not `localhost:8000` and not the Vercel API.

### Timeline starts but stops

Inspect the FastAPI container logs for provider authentication or model-ID
errors. Nginx already disables response buffering and allows one-hour SSE reads.

### LLM returns 401

Rotate or correct `NEBIUS_API_KEY` in Elastic Beanstalk environment properties,
then apply the configuration so the containers restart.
