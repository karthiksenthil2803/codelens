# PR Analysis Utility Setup Guide

This guide provides detailed instructions for setting up and running the PR Analysis Utility for Java Microservices.

## Prerequisites

- Python 3.10 or higher
- Git
- GitHub account with repository access
- LLM API access (e.g., OpenAI API key)

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd flask-template
```

## Step 2: Create and Activate Virtual Environment

**Using Python venv:**

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Using Conda (Alternative):**

If you have an existing conda environment at `e:\Github Repositories\codelens\.conda`:

**Windows:**
```bash
# Method 1: Activate using the full path
conda activate e:\Github Repositories\codelens\.conda

# Method 2: If it's a named environment
# First, list available environments
conda env list
# Then activate by name
conda activate environment_name
```

**macOS/Linux:**
```bash
# Method 1: Activate using the full path
conda activate /path/to/e:/Github\ Repositories/codelens/.conda

# Method 2: If it's a named environment
# First, list available environments
conda env list
# Then activate by name
conda activate environment_name
```

**Using Conda on Windows:**

Option 1: Use the provided batch file:
```
e:\Github Repositories\codelens\activate_conda.cmd
```

Option 2: Activate directly in Command Prompt:
```
conda activate e:\Github Repositories\codelens\.conda
```

Option 3: If you have Git Bash installed:
```bash
cd e:/Github\ Repositories/codelens/
./activate_conda.sh
```

Option 4: Using Windows Subsystem for Linux (WSL):
```bash
bash -c "e:/Github\ Repositories/codelens/activate_conda.sh"
```

**Note:** If you encounter issues with path-based activation, you can:
1. Use a named environment instead
2. Ensure conda is initialized in your shell with `conda init cmd.exe`
3. Or create a new conda environment with `conda create -n pranalysis python=3.10`

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

For development (including testing tools):
```bash
pip install -r dev-requirements.txt
```

## Step 4: Configure Environment Variables

1. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

2. Open the `.env` file and add the following values:
   ```
   # GitHub API configuration
   GITHUB_TOKEN=your_github_token_here
   
   # LLM API configuration
   LLM_API_KEY=your_llm_api_key_here
   LLM_API_URL=https://api.openai.com/v1/chat/completions
   LLM_MODEL=gpt-4
   
   # Flask configuration
   FLASK_APP=app.py
   FLASK_ENV=development
   ```

### Creating a GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name and select the `repo` scope
4. Click "Generate token" and copy the token value
5. Paste it as the value for `GITHUB_TOKEN` in your `.env` file

### Getting an LLM API Key

For OpenAI:
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key and paste it as the value for `LLM_API_KEY` in your `.env` file

## Step 5: Initialize the Repository Relationship Store

The system will automatically create the repository relationship store file at `data/repo_relationships.json` when needed.

## Step 6: Run the Application

**Development Mode:**
```bash
flask run --debug
```

**Using VS Code:**
1. Open the project in VS Code
2. Ensure the Python extension is installed
3. Press F5 or use the Run and Debug panel

## Step 7: Configure GitHub Webhooks

1. Go to your GitHub repository settings
2. Navigate to "Webhooks" > "Add webhook"
3. Set the Payload URL to your server URL with the webhook endpoint:
   - Local development (requires tunneling): `https://your-tunnel-url/webhook`
   - Production: `https://your-server-url/webhook`
4. Set Content type to `application/json`
5. Select "Let me select individual events" and choose "Pull requests"
6. Click "Add webhook"

### For Local Development Testing

For local development, you'll need a publicly accessible URL. You can use tools like:
- [ngrok](https://ngrok.com/) - `ngrok http 5000`
- [localtunnel](https://localtunnel.github.io/www/) - `lt --port 5000`

## Step 8: Set Up Repository Relationships

Use the API to define relationships between repositories for cross-repo analysis:

```bash
curl -X POST http://localhost:5000/api/relationships \
  -H "Content-Type: application/json" \
  -d '{
    "source": "owner/repo1", 
    "target": "owner/repo2", 
    "relationship_type": "depends-on"
  }'
```

## Step 9: Test the Setup

1. Create or update a PR in your GitHub repository
2. Verify that the webhook is triggered
3. Check the application logs for processing information
4. Verify that a comment is posted to your PR with the analysis

## Troubleshooting

### Webhook Not Triggering
- Verify the webhook configuration in GitHub
- Check that your server is publicly accessible
- Examine GitHub webhook delivery logs in repository settings

### Missing Comments on PR
- Verify your GitHub token has proper permissions
- Check application logs for API errors
- Ensure the PR payload is correctly formatted

### LLM Analysis Issues
- Verify your LLM API key
- Check if you have sufficient API credits/quota
- Examine the application logs for API response errors
