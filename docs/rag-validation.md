# Knowledge Base Retrieval

## Implementation

`search_knowledge_base()` calls the Bedrock Retrieve API with the configured Knowledge Base ID and the user's query. It uses `managedSearchConfiguration` with `rerankingModelType` set to `NONE`, joins retrieved content, and includes available document locations in a deduplicated source list. Including document locations supports checking where retrieved information originated; source display is an enhancement rather than a separate course requirement.

The source document is `product_catalog.txt` in S3. The implementation uses Bedrock Managed Knowledge Base because the lab role did not permit the OpenSearch provisioning operations specified in the course setup. OpenSearch Serverless is not part of the deployed architecture.

## Deployed validation

Prompt: `What are the benefits of the Platinum loyalty tier?`

The response contained the three expected benefits: free same-day shipping, a 15% discount, and priority customer support. See [the Runtime evidence](screenshots/03-rag-runtime.png).

The final response in this screenshot includes a blank `Source:` label. The tool's inclusion of document locations does not guarantee that the model displays a complete citation. A separate deployed Kindle query returned the S3 catalog URI, but consistent citation formatting is not claimed.

## Scope

The catalog contains course sample data. These observations demonstrate the tested responses, not correctness for every query or confirmation of current commercial policies. Tool invocation traces are not included in the screenshot evidence.
