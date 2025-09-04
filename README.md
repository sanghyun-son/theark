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
./scripts/run/start.sh

# Start with custom port
./scripts/run/start.sh --port 3000

# Start in production mode
./scripts/run/start.sh --prod

# Get help with options
./scripts/run/start.sh --help

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
# Run the comprehensive TheArk demo
uv run python examples/theark_demo.py
```

## 🛠️ Development

### Code Quality

```bash
# Run all quality checks
./scripts/dev/check.sh
```

### Testing

```bash
# Run all tests
./scripts/dev/test.sh

# Run specific test categories
./scripts/dev/test.sh tests/api/           # API tests
./scripts/dev/test.sh tests/core/          # Core functionality tests

# Run with different options
./scripts/dev/test.sh --integration        # Integration tests only
./scripts/dev/test.sh --unit              # Unit tests only
./scripts/dev/test.sh --log-debug         # With debug logging
./scripts/dev/test.sh --verbose           # Verbose output
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
- Run `./scripts/dev/check.sh` before committing
- Use `./scripts/dev/check.sh --fix` to auto-fix formatting issues
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🚀 **LLM Request 로깅 시스템**

### **개요**
LLM Request 로깅 시스템은 모든 LLM API 호출을 자동으로 추적하고 분석할 수 있게 해주는 범용적인 솔루션입니다.

### **주요 기능**
- **자동 로깅**: Context Manager를 사용하여 최소한의 코드로 자동 로깅
- **비용 추적**: OpenAI 가격 정책을 기반으로 한 자동 비용 계산
- **성능 모니터링**: 응답 시간, 토큰 사용량 등 상세한 메트릭
- **에러 추적**: 실패한 요청에 대한 자동 에러 로깅
- **확장성**: 다양한 LLM 사용 사례에 쉽게 적용 가능

### **사용 예시**

#### **1. 기본 사용법 (SummarizationService 통합)**
```python
from core.services import PaperSummarizationService

# 자동으로 LLM Request가 로깅됩니다
summary = await summarization_service.summarize_paper(
    paper=paper,
    db_session=db_session,  # 런타임에 주입
    llm_client=llm_client,
    language="Korean"
)
```

#### **2. 직접 사용법**
```python
from core.services import track_llm_request

async with track_llm_request(
    db_session=db_session,
    model="gpt-4",
    custom_id="user-123-summary",
    request_type="summarization",
    metadata={"language": "Korean", "content_length": 1000}
) as tracker:
    # 핵심 로직만 실행
    response = await llm_client.chat.completions.create(...)
    
    # 응답 설정 (자동 로깅을 위해)
    tracker.set_response(response)
    
    return response
```

#### **3. 고급 사용법**
```python
from core.services import LLMRequestTracker

async with LLMRequestTracker(
    db_session=db_session,
    model="gpt-4",
    custom_id="custom-analysis",
    request_type="analysis",
    metadata={"domain": "AI", "complexity": "high"}
) as tracker:
    # 커스텀 메타데이터 추가
    tracker.set_custom_metadata("user_preference", "detailed")
    
    # LLM 요청 실행
    response = await execute_llm_request()
    
    # 응답 설정
    tracker.set_response(response)
    
    return response
```

### **자동 로깅 정보**
- **기본 정보**: 모델, 제공자, 엔드포인트, 요청 타입
- **성능 메트릭**: 응답 시간, 토큰 사용량
- **비용 정보**: 예상 비용 (USD)
- **상태 정보**: 성공/실패/에러 상태
- **커스텀 데이터**: 사용자 정의 메타데이터

### **데이터베이스 스키마**
```sql
CREATE TABLE llm_request (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    custom_id TEXT,
    request_type TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost_usd REAL,
    response_time_ms INTEGER,
    http_status_code INTEGER,
    error_message TEXT,
    metadata TEXT
);
```

### **분석 및 모니터링**
```python
from core.database.repository import LLMRequestRepository

# 일일 비용 요약 (Pydantic 모델 반환)
cost_summary = llm_repo.get_cost_summary_by_date("2024-01-15")
print(f"총 비용: ${cost_summary.total_cost_usd}")
print(f"요청 수: {cost_summary.request_count}")

# 모델별 사용 통계 (타입 안전한 Pydantic 모델)
usage_stats = llm_repo.get_model_usage_stats("2024-01-01", "2024-01-31")
for model_name, stats in usage_stats.models.items():
    print(f"{model_name}: {stats.total_requests} requests, ${stats.total_cost_usd}")

# 기간별 총 비용
total_cost = llm_repo.get_total_cost_by_period("2024-01-01", "2024-01-31")
```

### **타입 안전성 및 모델 기반 설계**
- **Pydantic 모델**: `dict` 대신 타입 안전한 Pydantic 모델 사용
- **자동 검증**: 데이터베이스 응답의 자동 타입 검증
- **IDE 지원**: 완벽한 자동완성과 타입 힌트 지원
- **확장성**: 새로운 통계 필드 추가 시 모델만 수정하면 됨

### **장점**
1. **최소한의 코드**: `with` 문 내부에는 핵심 로직만
2. **자동 에러 처리**: 예외 발생 시 자동으로 에러 로깅
3. **런타임 의존성 주입**: DB 세션을 `__init__`이 아닌 런타임에 주입
4. **기존 상수 활용**: `core.constants`의 OpenAI 가격 정책 사용
5. **범용성**: summarization뿐만 아니라 모든 LLM 사용 사례에 적용 가능
