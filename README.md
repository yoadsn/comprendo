# Comprendo Project

## Purpose of the System

The Comprendo project is designed to handle business data extraction from documents, currently COA documents are the only supported document type. It leverages various AI models and APIs to accomplish this.

## Local Development Setup and Startup

To set up the project locally, follow these steps:

1. **Clone the Repository:**

   ```bash
   git clone <repository-url>
   cd comprendo
   ```

2. **Environment Configuration:**

   - Copy the `.env.template` to `.env` and fill in the necessary configurations. The mandatory configurations include:

     - `OPENAI_API_KEY`
     - `ANTHROPIC_API_KEY`
     - `GEMINI_API_KEY`
     - `GOOGLE_APPLICATION_CREDENTIALS` (As expected by the google-auth lib)
     - `GOOGLE_APPLICATION_CREDENTIALS_JSON_DUMP` (See below on how to create this from a valid credentials JSON file)
     - `DISABLE_AUTHENTICATION=True` (If not disabled, ensure `CLIENT_APP_0` is defined - See below)
     - `COA_EXPERT_0` (Required if not in mock mode, choose from: `anthropic-claude-3-5-sonnet`, `gemini-1-5-flash`, `vertexai-gemini-1-5-flash`)
     - [Add any other mandatory configurations you identify]

   - **Note:** `MOCK_MODE` should generally be disabled even in development - you can enable it per-request by sending the "x-comprendo-mock-mode=True" header or setting a mock-only user and authenticating with that user.

3. **"CLIENT_APP_X" env settings**

   - These are used to authenticate requests to the API.
   - To simplify deployments - auth currently leverages simple env variables.
   - It supports up to 10 (0..9) different client apps.
   - Each client app value has the structure `key;name;mock-only` - the `key` is used for authentication and the `name` is used for logging.
   - The `mock-only` flag indicates that the client app is mock-only and unable to choose to disable mock mode. (always on)
   - See the API docs for more details on how to authenticate to the API.

4. **Install Dependencies:**

   - Use the `requirements.txt` for installing necessary packages:
     ```bash
     pip install -r requirements.txt
     ```

5. **Start the Development Server:**
   - Use `uvicorn` to start the server:
     ```bash
     uvicorn server:app --reload
     ```

## Production Deployment Model

The production deployment involves the following steps:

1. **Build the Docker Image:**

   - Build the container for Azure deployment targeting `linux/amd64`:
     ```bash
     docker build --tag comprendo-api --platform linux/amd64 .
     ```

2. **Push to Azure Container Registry (ACR):**

   - Tag and push the image:
     ```bash
     docker tag comprendo-api comprendocr.azurecr.io/comprendo-api
     docker push comprendocr.azurecr.io/comprendo-api
     ```

3. **Deploy to Azure Container Apps:**
   - Start a Container App from the pushed image. Configuration is expected to be set via environment variables.

> Note: Detailed instructions on setting up Azure Container Apps or ACR are out of scope for this document.

> **Optional:** If not using Azure Application Insights, omit `APPLICATIONINSIGHTS_CONNECTION_STRING`.
