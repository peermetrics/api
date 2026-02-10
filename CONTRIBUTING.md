# Contributing to API Server

> [!Note]
> This is the API server component of the peermetrics WebRTC monitoring service. For the full project, see [peermetrics](https://github.com/peermetrics/peermetrics).

We welcome contributions to the API server! This guide will help you set up your development environment and understand our contribution workflow.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.8
- PostgreSQL
- Redis
- pip
- virtualenv (recommended)
- Git

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/peermetrics/api-server.git
cd api-server
```

### 2. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the `.env` file and update the values as needed:

```bash
cp .env .env.local
```

Key environment variables to configure:

- `DEBUG`: Set to `True` for development
- `SECRET_KEY`: Django secret key
- `INIT_TOKEN_SECRET`: Used to generate JWT tokens
- `SESSION_TOKEN_SECRET`: Used to encrypt session cookies
- `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`: PostgreSQL connection details
- `REDIS_HOST`: Redis server location
- `WEB_DOMAIN`: Domain for the web interface (default: `localhost:8080`)

### 5. Set Up the Database

Run Django migrations to create the database schema:

```bash
python manage.py migrate
```

### 6. Create a Superuser (Optional)

To access the Django admin interface:

```bash
python manage.py createsuperuser
```

### 7. Populate Test Data

Use the `populate_db.py` script to generate test data:

```bash
# Generate data for the last 7 days
python populate_db.py 7

# Clean all test data
python populate_db.py clean
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`.

## Project Structure

```
api-server/
├── api/                    # Django project settings
│   ├── settings.py        # Main settings file
│   └── urls.py            # Root URL configuration
├── app/                   # Main application
│   ├── models/           # Database models
│   ├── views/            # API views/endpoints
│   ├── middleware.py     # Custom middleware
│   └── decorators.py     # Custom decorators
├── static/               # Static files
├── config_populate_db/   # Test data configuration
├── manage.py             # Django management script
├── populate_db.py        # Script to populate test data
└── requirements.txt      # Python dependencies
```

### Key Files

- **manage.py**: Standard Django management script for running commands
- **populate_db.py**: Generates realistic test data for development
- **config_populate_db**: Configuration files for test data generation

### Models

The main models are located in `app/models/`:

- **Organization**: Groups multiple apps
- **App**: Groups conferences
- **Conference**: Represents a call between participants
- **Participant**: A user participating in conferences
- **Session**: A participant's presence in a conference
- **GenericEvent**: Events collected during calls

### Views

API endpoints are organized in `app/views/` and split into:

- **Public routes**: Used by the SDK (e.g., `/initialize`, `/events/*`, `/stats`)
- **Private routes**: Used for data queries (e.g., `/sessions`, `/conferences`, `/participants`)

## Development Workflow

### 1. Create a New Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation changes

### 2. Make Your Changes

Follow these guidelines:

- Write clear, self-documenting code
- Add comments for complex logic
- Keep functions focused and small
- Follow Django best practices

### 3. Test Your Changes

Run the development server and test your changes manually:

```bash
python manage.py runserver
```

Use the Django admin interface at `http://localhost:8000/admin` to inspect data.

### 4. Commit Your Changes

Write clear commit messages:

```bash
git add .
git commit -m "Add feature: brief description of changes"
```

Good commit message format:
```
Add feature: allow filtering conferences by date range

- Added date_from and date_to query parameters
- Updated Conference view to handle date filtering
- Added validation for date format
```

## Django Admin Interface

Access the admin interface at `http://localhost:8000/admin` to:

- View and edit raw data
- Inspect model relationships
- Debug data issues
- Manually create test records

Login with the superuser credentials you created during setup.

## API Development Guidelines

### Adding New Endpoints

1. Define the view in `app/views/`
2. Add the URL pattern in `api/urls.py`
3. Implement authentication/authorization if needed
4. Test the endpoint manually

### Model Changes

When modifying models:

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

Always review the generated migration files before committing.

### Authentication Patterns

- Public endpoints use JWT tokens generated via `/initialize`
- Private endpoints require authentication (check existing views for patterns)
- Use the decorators in `app/decorators.py` for common auth patterns

### Error Handling

- Return appropriate HTTP status codes
- Provide clear error messages in the response
- Log errors for debugging
- Follow the error handling patterns in existing views

## Submitting Changes

### 1. Push Your Branch

```bash
git push origin feature/your-feature-name
```

### 2. Create a Pull Request

- Provide a clear title and description
- Reference any related issues
- Explain what changes were made and why
- Include any testing steps

### PR Description Template

```markdown
## Description
Brief description of changes

## Changes Made
- List of specific changes
- Another change

## Testing
How to test these changes

## Related Issues
Fixes #123
```

### 3. Code Review Process

- A maintainer will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged

### CI/CD Checks

Pull requests trigger automated workflows (see `.github/workflows/`):
- Docker image builds
- Code quality checks

Ensure all checks pass before requesting review.

## Getting Help

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/peermetrics/api-server/issues)
- **Discussions**: Ask questions in the main [peermetrics repository](https://github.com/peermetrics/peermetrics)
- **Documentation**: Check the [README](README.md) for project overview

## Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Keep line length reasonable (under 100 characters when possible)
- Add docstrings to functions and classes

## Additional Notes

### Working with populate_db.py

The `populate_db.py` script is useful for:
- Generating realistic test data
- Testing with different data volumes
- Simulating various conference scenarios

You can customize the test data by modifying files in `config_populate_db/`.

### Database Tips

- Use `python manage.py dbshell` to access the PostgreSQL shell
- Run `python manage.py showmigrations` to see migration status
- Use `python manage.py sqlmigrate app_name migration_name` to view SQL for a migration

Thank you for contributing to peermetrics API server!