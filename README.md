# TheArk 🚀

[![CI](https://github.com/sanghyun-son/theark/actions/workflows/ci.yml/badge.svg)](https://github.com/sanghyun-son/theark/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A comprehensive paper management system with ArXiv crawling, AI-powered summarization, and LLM request tracking. Built with modern Python practices and FastAPI for scalable backend services.

## ✨ Features

- **🔍 ArXiv Crawling**: Automated paper discovery and metadata extraction
- **🤖 AI Summarization**: OpenAI-powered abstract summarization with structured output
- **📊 LLM Tracking**: Comprehensive monitoring of API usage and costs
- **🌐 FastAPI Backend**: RESTful API server for frontend integration
- **💾 Database Management**: SQLite-based storage with LLM request tracking
- **🔒 Type Safety**: Full type hints with mypy strict checking
- **🧪 Comprehensive Testing**: Unit and integration tests with pytest
- **📋 Code Quality**: Automated formatting, linting, and type checking

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- OpenAI API key (for summarization features)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd theark

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e .

# Set up environment
export OPENAI_API_KEY="your-api-key-here"
```

### Running the API Server

```bash
# Start the FastAPI server (default settings)
./run.sh

# Start with custom port
./run.sh --port 3000

# Start in production mode
./run.sh --prod

# Get help with options
./run.sh --help

# Server will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

### API Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /openapi.json` - OpenAPI schema
- `GET /favicon.ico` - Favicon file

### Running the Demo

```bash
# Run the ArXiv crawler demo with summarization
uv run python examples/arxiv_crawler_demo.py
```

## 🛠️ Development

### Code Quality

```bash
# Run all quality checks
./check.sh

# Individual checks
uv run ruff check .     # Linting
uv run black .          # Code formatting
uv run isort .          # Import sorting
uv run mypy .           # Type checking

# Auto-fix issues
./check.sh --fix
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/api/           # API tests
uv run pytest tests/core/          # Core functionality tests
```

## 🏗️ Architecture

### Core Components

- **🔍 ArXiv Crawler**: Handles paper discovery and metadata extraction
- **🤖 Summarization Service**: AI-powered abstract analysis
- **📊 LLM Tracking**: Monitors API usage and calculates costs
- **🌐 FastAPI Server**: RESTful API for frontend integration

### Database

- **💾 Main Database**: SQLite-based paper and summary storage
- **📈 LLM Database**: Separate database for API request tracking

### Project Structure

```
theark/
├── api/                    # FastAPI backend server
│   ├── routers/           # API route modules
│   ├── dependencies.py    # Dependency injection
│   └── templates/         # HTML templates
├── core/                  # Core utilities and logging
├── crawler/               # ArXiv crawling and processing
│   ├── database/         # Database models and management
│   └── summarizer/       # AI summarization services
├── static/               # Static files (favicon, etc.)
├── tests/                # Test suite
├── examples/             # Demo and example scripts
└── db/                   # Database files
```

## 📋 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write tests for new functionality
- Run `./check.sh` before committing
- Use `./check.sh --fix` to auto-fix formatting issues
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
