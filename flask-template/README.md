# Flask Template

This sample repo contains the recommended structure for a Python Flask project. In this sample, we use `flask` to build a web application and the `pytest` to run tests.

 For a more in-depth tutorial, see our [Flask tutorial](https://code.visualstudio.com/docs/python/tutorial-flask).

 The code in this repo aims to follow Python style guidelines as outlined in [PEP 8](https://peps.python.org/pep-0008/).

## Running the Sample

To successfully run this example, we recommend the following VS Code extensions:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy)
- [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) 

- Open the template folder in VS Code (**File** > **Open Folder...**)
- Create a Python virtual environment using the **Python: Create Environment** command found in the Command Palette (**View > Command Palette**). Ensure you install dependencies found in the `pyproject.toml` file
- Ensure your newly created environment is selected using the **Python: Select Interpreter** command found in the Command Palette
- Run the app using the Run and Debug view or by pressing `F5`
- To test your app, ensure you have the dependencies from `dev-requirements.txt` installed in your environment
- Navigate to the Test Panel to configure your Python test or by triggering the **Python: Configure Tests** command from the Command Palette
- Run tests in the Test Panel or by clicking the Play Button next to the individual tests in the `test_app.py` file

# PR Analysis Utility for Java Microservices

This Flask application provides automated analysis of Pull Requests (PRs) in Java Spring Boot microservice repositories stored on GitHub. It uses LLMs to generate smart analysis and suggestions for PR reviews.

## Features

- Webhook integration with GitHub for automatic PR analysis
- Cross-repository dependency analysis
- AI-powered code review suggestions using LLMs
- Impact assessment for Java microservices

## Setup Instructions

### Using Conda Environment

If you prefer using conda instead of venv, you can use an existing conda environment at `e:\Github Repositories\codelens\.conda`:

**Windows:**
```bash
# Activate existing conda environment
conda activate e:\Github Repositories\codelens\.conda

# Or if using a named environment
conda activate myenv
```

**macOS/Linux:**
```bash
# Activate existing conda environment
conda activate /path/to/e:/Github\ Repositories/codelens/.conda

# Or if using a named environment
conda activate myenv
```

### 1. Set Up the Environment

1. Open the project folder in VS Code or your preferred editor
2. Create a Python virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   For development:
   ```bash
   pip install -r dev-requirements.txt
   ```

### 2. Configure Environment Variables

1. Create a `.env` file in the project root (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
2. Set up the required environment variables in the `.env` file:
   - `GITHUB_TOKEN`: Your GitHub personal access token with repo permissions
   - `LLM_API_KEY`: API key for the LLM service (e.g., OpenAI)
   - `LLM_MODEL`: Model to use (default is "gpt-4")

### 3. Configure GitHub Webhooks

1. Go to your GitHub repository settings
2. Navigate to "Webhooks" > "Add webhook"
3. Set the Payload URL to `https://your-server-url/webhook`
4. Set Content type to `application/json`
5. Select "Let me select individual events" and choose "Pull requests"
6. Click "Add webhook"

## Running the Application

### Development Mode

```bash
flask run --debug
```

Or launch using VS Code's debugger by pressing F5.

### Production Mode

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn app:app
```

## Setting Up Repository Relationships

To define relationships between repositories (for cross-repo analysis), use the API:

```bash
curl -X POST http://localhost:5000/api/relationships \
  -H "Content-Type: application/json" \
  -d '{"source": "owner/repo1", "target": "owner/repo2", "relationship_type": "depends-on"}'
```

Or access the API in your browser at: `http://localhost:5000/api/relationships`

## Running Tests

```bash
pytest
```

## Project Structure

- `app.py` - Main Flask application
- `services/` - Core services for PR analysis
  - `repo_relationship.py` - Manages repository relationships
  - `pr_analyzer.py` - Orchestrates PR analysis
  - `dependency_mapper.py` - Maps component dependencies
  - `context_generator.py` - Generates LLM prompts
  - `llm_engine.py` - Handles LLM API integration
  - `github_bot.py` - Posts results to GitHub
- `templates/` - HTML templates for web interface
- `static/` - CSS and other static assets

## Activating Conda Environment on Windows

### Option 1: Using Git Bash
If you have Git installed on Windows:
1. Open Git Bash
2. Navigate to the repository directory:
   ```bash
   cd e:/Github\ Repositories/codelens/
   ```
3. Run the activation script:
   ```bash
   ./activate_conda.sh
   ```

### Option 2: Using Command Prompt or PowerShell

1. Open Command Prompt or PowerShell
2. Navigate to the repository directory:
   ```bash
   cd e:\Github Repositories\codelens
   ```
3. Run the activation script:
   ```bash
   call activate_conda.bat
   ```

### Option 3: Manually Activating

1. Open Command Prompt
2. Navigate to the Scripts directory of your conda installation:
   ```bash
   cd C:\path\to\your\conda\Scripts
   ```
3. Activate the base environment:
   ```bash
   activate
   ```
4. Navigate back to your project directory and activate the desired environment:
   ```bash
   cd e:\Github Repositories\codelens
   activate myenv
   ```
