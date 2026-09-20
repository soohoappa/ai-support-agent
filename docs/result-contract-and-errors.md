# Calculation contract and Gateway failure handling

## Calculation result

`calculate_loyalty_discount` returns a JSON object encoded as a string. Successful sandbox output is decoded from `structuredContent.stdout`, so callers receive calculation fields directly rather than a nested execution envelope.

Both normal and fallback results have the same keys and types:

| Field | Type | Meaning |
| --- | --- | --- |
| points_redeemed | integer | Points spent; zero in the tier-only fallback |
| points_discount | number | Currency discount from points; zero in fallback |
| tier_discount | number | Currency discount for the tier |
| tier_discount_pct | number | Percentage in percent units: Gold = 10.0, Platinum = 15.0 |
| final_total | number | Amount after applicable discounts |
| total_savings | number | Original amount minus final total |
| points_earned | integer | Estimated purchase points; zero in fallback |
| remaining_points | integer | Starting points minus redeemed points plus earned points |
| fallback | boolean | Whether the sandbox calculation was unavailable |
| message | string | Calculation mode explanation |

Fallback calculates only the tier discount. It does not redeem or credit points, so remaining_points equals the original balance. For 4250 points, Gold, and a $150 standard order, normal final_total is 99.0 and remaining_points is 349. Fallback final_total is 135.0 and remaining_points is 4250. Both report tier_discount_pct = 10.0.

## Gateway errors

`SupportGatewayClient` extends `MCPClient`. Connection and tool discovery failures become concise operation-specific errors. Tool exceptions and MCP error results become safe tool error responses and cause the request to return status `error`, even if the model attempts to summarize them as success. Upstream error text is not included in these user-facing responses. A refund initiation failure advises checking status before retrying because the remote outcome may be unknown.

## Controlled offline verification

Run from the repository root:

```cmd
python -m unittest discover -s tests -v
```

[Recorded results](test-results/offline-contract-tests.txt) cover matching calculation keys/types, sandbox error fallback, Gateway connection/discovery exceptions, timeout and execution exceptions, returned MCP errors, and a successful request after a simulated connection failure. These tests execute the actual function/class bodies with simulated service dependencies and do not call AWS. They are controlled failure evidence, not live Gateway or model evidence.

## AgentCore CLI invocation evidence

The SDK deployment must also be invoked using the actual AgentCore CLI for the required submission artifact. The starter toolkit configuration's `bedrock_agentcore.agent_id` and `agent_arn` must reference the existing SDK-created Runtime. This connects the caller; it does not redeploy resources. If resources have been deleted, restore the lab deployment before attempting invocation.

In Windows CMD with the awsagent environment active, use the Python toolkit executable explicitly to avoid resolving the separate npm CLI:

```cmd
"%CONDA_PREFIX%\Scripts\agentcore.exe" invoke "{\"prompt\":\"Can you track order ORD-001?\",\"customer_id\":\"CUST-123\",\"session_id\":\"review-order\"}" --session-id "review-order-session-0000000000000001"
```

The [CLI invocation screenshot](screenshots/08-agentcore-invoke-runtime.png) includes the command, Runtime ARN, and returned response. It demonstrates cloud invocation, not exact delivery-date agreement with the earlier order test. Do not use `--local` or `--dev` for this artifact. Use the boto3 ZIP update workflow for deploying code changes; the old container deployment configuration is not the ZIP deployment definition.

## Controlled test screenshots

- [Gateway failure and next-request recovery](screenshots/09-gateway-controlled-failure.png).
- [Normal and fallback result contracts](screenshots/10-loyalty-result-contract.png).

Both screenshots are offline test evidence using simulated service dependencies.
