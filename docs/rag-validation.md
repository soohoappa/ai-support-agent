\# RAG Implementation and Validation



\## Infrastructure decision



The course setup specifies Amazon OpenSearch Serverless and

Amazon Titan Text Embeddings v2.



The Udacity lab role denied:

\- aoss:ListCollections

\- aoss:CreateSecurityPolicy

\- s3vectors:CreateVectorBucket



OpenSearch Serverless creation failed. An alternative attempt

using Amazon S3 Vectors also failed due to missing permissions.



The implementation therefore uses Amazon Bedrock Managed Knowledge Base

with Amazon Titan Text Embeddings v2 (1024 dimensions).



The application continues to use the Bedrock Retrieve API through

the search\_knowledge\_base tool. Managed retrieval uses

managedSearchConfiguration with rerankingModelType set to NONE.



\## Data ingestion



\- Source file: product\_catalog.txt

\- Ingestion status: COMPLETE

\- Documents scanned: 1

\- New documents indexed: 1

\- Failed documents: 0



\## Local validation



\### Documented question



Question: What are the benefits of the Platinum loyalty tier?



Observed: The agent returned free same-day shipping, a 15% discount,

and priority customer support, with the source URI.



\### Undocumented question



Question: Does the Diamond loyalty tier include free international shipping?



Observed: The agent stated that the retrieved information did not

document the requested tier or benefit and suggested contacting support.

The final tested response included one source URI.



Earlier responses inferred domestic shipping coverage and repeated

the source URI. Prompt clarification and source deduplication in the

retrieval tool addressed these issues in the latest observed response.



\## Limitations



These are local checks, not deployed AgentCore acceptance tests.

Passing these examples does not guarantee grounded answers for all inputs.

The catalog is course data, not verified current Amazon policy.

Other failure, access-control, and security tests remain pending.
