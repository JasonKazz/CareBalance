# Provider check — October 10, 2026

One real Gemini 3.8 Flash call extracted all six exact rates from the fictional sample offer. All six quotes passed local source/code/amount presence checks. Measured extraction: **3.81 seconds**. Usage: **392 input tokens, 485 output tokens**. Estimated cost: **$0.002113**. This is one synthetic-document test, not an accuracy estimate for real contracts, a browser end-to-end benchmark, or a latency guarantee.

Gemini 2.5 Flash initially returned a model-unavailable response for this account; the adapter was migrated to the provider-recommended 3.8 Flash. No sensitive documents were used.

Official references consulted:

- [Gemini 3.8 model, API changes, and introductory pricing](https://ai.google.dev/gemini-api/docs/generate-content/latest-model)
- [Structured extraction](https://ai.google.dev/gemini-api/docs/structured-output)
- [Document processing](https://ai.google.dev/gemini-api/docs/document-processing)

The estimator uses $0.75 per million input tokens and $3.75 per million output/thinking tokens through December 2026; announced standard prices double in January 2027. Actual bills may differ. No search grounding is used. Quotas depend on account/project and are not assumed; 429 errors are surfaced without retries. Provider data handling is separate from this app's no-storage behavior.

A separate browser check uploaded the same fictional TXT and CSV from disk, selected Gemini, acknowledged processing, reviewed six source-supported rates, and reproduced the −$25,700 matched annual difference. No end-to-end browser timing was recorded. The standard sample path, source highlighting, and 5% counteroffer were also checked visually. PDF text extraction passed an automated test with a generated text-based PDF; scanned PDFs remain unsupported.
