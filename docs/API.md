
# COA Extraction Service API

## Overview

The COA Extraction Service processes Certificates of Analysis (COA) documents, parses their content, and extracts measurement data based on the provided request parameters. This service supports multiple input files in PDF or PNG formats and allows the caller to define expected measurements for extraction and validation.

---

## API Endpoint

**URL:**  
`https://{base_url}/extract/coa`

**Method:**  
`GET`

**Content Type:**  
Multipart Form-Data

---

## Request Parameters

1. **`files`** (required):  
   - One or more COA documents to process.
   - Supported formats: `PDF` or `PNG`.  
   - Example: `files=@"/path/to/document.pdf"`

2. **`request`** (required):  
   - A JSON string defining the extraction request.
   - Example structure:
     ```json
     {
       "id": "<unique_request_id>",
       "order_number": "<purchase_order_number>",
       "measurements": [
         {
           "id": "<measurement_id>",
           "name": "<measurement_name>",
           "qualitative": <true_or_false>
         }
       ]
     }
     ```
   - **Attributes:**
     - `id` (string): Unique identifier for the request.
     - `order_number` (string): The purchase order number related to the COA documents.
     - `measurements` (array): A list of expected measurements to extract.
       - `id` (string): Unique identifier for the measurement (optional, can be `null` if not known).
       - `name` (string): Name or label of the measurement.
       - `qualitative` (boolean): Indicates if the measurement is qualitative (`true`) or quantitative (`false`).

---

## Example Request

```bash
curl --location --request GET 'https://{base_url}/extract/coa' \
--form 'files=@"/path/to/document1.pdf"' \
--form 'files=@"/path/to/document2.png"' \
--form 'request="{
  \"id\": \"12345\",
  \"order_number\": \"98765\",
  \"measurements\": [
    {\"id\": \"1\", \"name\": \"appearance_at_20_deg\", \"qualitative\": true},
    {\"id\": \"2\", \"name\": \"ph_level\", \"qualitative\": false},
    {\"id\": \"3\", \"name\": \"viscosity_at_25_deg\", \"qualitative\": false}
  ]
}"'
```

---

## Response Format

The response is a JSON object with the extracted results. It includes batch-specific details, extracted measurements, and status indicators.

### Response Attributes:

- **`request_id`** (string): The request's unique identifier.
- **`order_number`** (string): The purchase order number from the request.
- **`batches`** (array): List of batches identified in the documents.
  - **`batch_number`** (string): The batch number from the document.
  - **`expiration_date`** (string): The expiration date of the batch (if available).
  - **`results`** (array): Extracted measurement results for the batch.
    - **`measurement_id`** (string/null): ID of the measurement from the request, or `null` if not matched.
    - **`measurement_name`** (string): Name of the measurement as it appears in the document.
    - **`value`**: Extracted measurement value.
    - **`accept`** (boolean): Whether the measurement value is within acceptable limits.
    - **`flag_uncertain`** (boolean): Indicates if the result is uncertain due to low confidence or ambiguous data.

- **`identification_warning`** (boolean): Indicates if the document parsing encountered potential identification issues.
- **`mock`** (boolean): Indicates if the service is running in a mock or test mode.

---

## Example Response

```json
{
    "request_id": "12345",
    "order_number": "98765",
    "batches": [
        {
            "batch_number": "AB123",
            "expiration_date": "2025-12-31",
            "results": [
                {
                    "measurement_id": "1",
                    "measurement_name": "appearance_at_20_deg",
                    "value": true,
                    "accept": true,
                    "flag_uncertain": false
                },
                {
                    "measurement_id": null,
                    "measurement_name": "unknown_measurement",
                    "value": 45.67,
                    "accept": false,
                    "flag_uncertain": true
                }
            ]
        }
    ],
    "identification_warning": false,
    "mock": false
}
```

---

## Notes

- If a measurement in the request cannot be found in the document, its `measurement_id` will be `null` in the response.
- For ambiguous or low-confidence matches, the `flag_uncertain` field will be set to `true`.
- The service allows multiple input documents for processing in a single request.
