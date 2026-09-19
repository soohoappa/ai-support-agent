# Customer Support Agent on Amazon Bedrock AgentCore

An Udacity customer support project implementing order tracking, refunds, catalog retrieval, cross-session memory, loyalty calculations, and web browsing. The agent is deployed to Amazon Bedrock AgentCore Runtime in `us-east-1` and was tested through the AWS SDK.

## Architecture

```text
SDK client -> AgentCore Runtime -> Strands Agent (Amazon Nova 2 Lite)
  |-- AgentCore Gateway -> API Gateway -> order-tracker Lambda
  |                    -> refund-processor Lambda
  |-- Bedrock Knowledge Base -> product_catalog.txt in S3
  |-- AgentCore Memory -> customer facts and preferences
  |-- AgentCore Code Interpreter -> loyalty calculation
  `-- AgentCore Browser -> live page title

Runtime logs -> CloudWatch ERROR metric filter -> ErrorCount alarm
```

The Lambda functions provide course sample data. Refund approval responses are simulated; they do not transfer money. Product details and policies are course catalog content, not independently verified current retailer policies.

## Project files

| Path | Purpose |
| --- | --- |
| `main.py` | Agent entrypoint, tools, and memory hooks |
| `lambda/order_tracker.py` | Sample order and customer lookup |
| `lambda/refund_processor.py` | Sample refund and return-label tools |
| `lambda/lambda_schema` | Direct Lambda tool schemas |
| `product_catalog.txt` | Knowledge Base source document |
| `pyproject.toml`, `uv.lock`, `requirements.txt` | Python dependency configuration |
| `agentcore/agentcore.json` | Local AgentCore Inspector configuration |
| `docs/screenshots/` | Runtime and optional local test evidence |
| `docs/reflection.md` | Project reflection |
| `docs/rag-validation.md` | Retrieval implementation and observed results |

## Setup

Use Python 3.14, AWS credentials for the lab account, and region `us-east-1`. Install dependencies using `uv sync` from the project directory. The Runtime package uses Linux ARM64 dependencies rather than Windows binaries.

Configure these resources before running the agent:

1. Deploy the two Lambda functions and the order API routes: `GET /orders/{order_id}`, `GET /customers/{customer_id}`, and `GET /customers/{customer_id}/orders`.
2. Register the `order-tracker` API Gateway target and `refund-processor` Lambda target in AgentCore Gateway.
3. Upload `product_catalog.txt` to S3, connect the Knowledge Base, and complete ingestion.
4. Create AgentCore Memory with semantic and user-preference strategies at `cs_agent/{actorId}/facts` and `cs_agent/{actorId}/preferences`.
5. Set `MEMORY_ID` and `REGION` in `main.py` for the target account. Set `GATEWAY_URL` and `KB_ID` in the process environment. The Gateway URL must include `/mcp`.

Windows CMD example:

```cmd
set "AWS_DEFAULT_REGION=us-east-1"
set "GATEWAY_URL=<your-gateway-url>"
set "KB_ID=<your-knowledge-base-id>"
```

The implementation uses `global.amazon.nova-2-lite-v1:0`. The course setup names Nova Lite; this submission uses Nova 2 Lite. The course specifies OpenSearch Serverless for vector storage; this lab implementation uses **Bedrock Managed Knowledge Base** because the lab role did not permit the required OpenSearch provisioning operations. This is an infrastructure deviation, not a claim that OpenSearch was deployed.

The lab Gateway uses inbound authorization `NONE`. Its outbound service role retains permission to invoke the API and Lambda targets. The deployed Runtime uses IAM authorization. This configuration is for the lab demonstration; production would require authenticated Gateway access and customer authorization.

## Deployment

The submitted agent runs as a Python 3.14 ZIP deployment created with boto3 `create_agent_runtime`. Dependencies were packaged for `aarch64-manylinux_2_28`, with `main.py` at the ZIP root and Linux executable permissions preserved. The ZIP was uploaded to S3 and referenced with:

```python
agentRuntimeArtifact={
    "codeConfiguration": {
        "code": {"s3": {"bucket": bucket, "prefix": key}},
        "runtime": "PYTHON_3_14",
        "entryPoint": ["main.py"],
    }
}
```

Runtime configuration uses HTTP, PUBLIC networking, an execution role, and the `GATEWAY_URL` and `KB_ID` environment variables. The execution role needs the applicable model, memory, Code Interpreter, browser, logging, and deployment-package permissions, including `bedrock:Retrieve` for the configured Knowledge Base. Browser permissions include session start/get/stop and `ConnectBrowserAutomationStream` for `aws.browser.v1`.

The deployed Runtime reached `READY`. ZIP build directories, deployment response files, and account-specific working scripts are excluded from Git. The local Inspector configuration does not manage this SDK-created deployment.

## Invoke the deployed agent

Set `AGENT_RUNTIME_ARN` to the deployed Runtime ARN. Run this Python example with valid caller credentials. The caller needs `bedrock-agentcore:InvokeAgentRuntime` permission.

```python
import json
import os
import uuid
from datetime import datetime
from time import perf_counter

import boto3
from botocore.config import Config

client = boto3.client(
    "bedrock-agentcore", region_name="us-east-1",
    config=Config(read_timeout=180, retries={"total_max_attempts": 1}),
)
prompt = input("Prompt: ").strip()
if not prompt:
    raise SystemExit("Please enter a prompt.")
session_id = str(uuid.uuid4())
print("Customer: CUST-123")
print("Session:", session_id)
print("Request time:", datetime.now().astimezone().isoformat(timespec="seconds"))
started = perf_counter()
response = client.invoke_agent_runtime(
    agentRuntimeArn=os.environ["AGENT_RUNTIME_ARN"],
    runtimeSessionId=session_id,
    qualifier="DEFAULT",
    contentType="application/json",
    payload=json.dumps({
        "prompt": prompt, "customer_id": "CUST-123", "session_id": session_id,
    }).encode(),
)
body = response["response"].read().decode()
print("Response time:", datetime.now().astimezone().isoformat(timespec="seconds"))
print(f"Elapsed: {perf_counter() - started:.2f} seconds")
print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
```

## Runtime test evidence

The following screenshots show calls to the deployed Runtime. A returned `status: ok` alone is not sufficient: the response content was checked against each scenario.

| Test | Prompt and observed result | Evidence |
| --- | --- | --- |
| 1. Orders | `Can you track order ORD-001?` Shipped via UPS, tracking `TRK987654321`, delivery `2026-09-21`. | [Runtime screenshot](docs/screenshots/01-order-tracking-runtime.png) |
| 2. Refunds | `I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.` Approved for $139.99, refund ID returned, 3–5 business days. | [Runtime screenshot](docs/screenshots/02-refund-runtime.png) |
| 3. RAG | `What are the benefits of the Platinum loyalty tier?` Free same-day shipping, 15% discount, and priority support. | [Runtime screenshot](docs/screenshots/03-rag-runtime.png) |
| 4. Memory | `Hi, I am Jane. I prefer concise responses.` Then `Do you remember my name and communication preference?` Same customer, distinct session UUIDs; Jane and concise responses recalled. | [Both sessions](docs/screenshots/04-memory-runtime.png) |
| 5. Calculation | `I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.` Redeemed 4,000 points; discounts $40 and $11; final $99; earned 99 points; remaining 349. | [Runtime screenshot](docs/screenshots/05-loyalty-runtime.png) |
| 6. Browser | `Go to https://www.udacity.com and tell me the page title.` Returned `Learn the Latest Tech Skills; Advance Your Career \| Udacity`. | [Runtime screenshot](docs/screenshots/06-browser-runtime.png) |

Memory extraction is asynchronous. The captured requests were approximately 2 minutes 43 seconds apart. This customer already had test history, so the response also included prior order information. The screenshot demonstrates recall across different sessions; it is not a clean-room memory isolation test.

The Browser test follows the Udacity URL in the classroom task instructions. The starter README uses Amazon.com instead. Optional `*-local.png` screenshots show the local Inspector and are not cloud deployment evidence.

## CloudWatch monitoring

The Runtime log group has an `ERROR` metric filter named `CustomerSupportErrorFilter`:

- Namespace: `CustomerSupportAgent`; metric: `ErrorCount`.
- Matching event value: `1`; default value: `0`; unit: `Count`.
- Alarm: `CustomerSupportAgent-HighErrorCount`.
- Statistic: **Sum**; period: **5 minutes**; threshold: **greater than 5**.
- Evaluation: **1 out of 1**; missing data: **not breaching**.
- No SNS notifications or automated actions are configured.

[Alarm configuration evidence](docs/screenshots/07-cloudwatch-alarm.png). The screenshot records creation and the configured threshold, not an induced ALARM transition. The metric counts matching log events, not necessarily unique failed requests; tool errors handled without an ERROR log are not counted.

## Reflection and cleanup

See [the project reflection](docs/reflection.md).

After preserving the submission and evidence, delete the SDK-created Runtime and verify removal in the console. The starter toolkit's `agentcore destroy` must not be assumed to discover a Runtime created separately through boto3. Remove the lab Gateway and targets, Memory, Knowledge Base, S3 data/deployment artifacts, API Gateway, Lambda functions, CloudWatch alarm/filter, and any dedicated deployment resources such as CodeBuild and ECR. Remove unused project-only IAM roles after dependent resources are deleted. Check for any storage created during setup; deleting a Knowledge Base alone does not remove all underlying storage. Cleanup is a remaining operational step until verified.
