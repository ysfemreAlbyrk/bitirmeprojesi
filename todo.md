# VibeTale Backend - Implementation Plan

## Order of Implementation

### Phase 1: Infrastructure & Foundation
1. **Redis Setup** - Install and configure Redis for caching and Celery
2. **Logging System** - Implement structured logging with log levels and file rotation
3. **File Upload Security Validation** - Add MIME type validation, magic bytes verification, file size limits

### Phase 2: Database & API Improvements
4. **Database Connection Pooling** - Configure Supabase client connection pooling
5. **Pagination** - Add pagination to all list endpoints (books, chapters, text_chunks)
6. **Rate Limiting** - Implement rate limiting middleware for API endpoints

### Phase 3: Background Processing
7. **Background Task Queue (Celery)** - Set up Celery with Redis for async book processing

### Phase 4: Testing
8. **Unit Tests Setup** - Configure pytest, write unit tests for core services
9. **Integration Tests Setup** - Configure test database, write integration tests for API endpoints

## Detailed Implementation Steps

### 1. Redis Setup
- Add redis to requirements.txt
- Update .env.example with Redis configuration
- Create Redis client wrapper
- Update docs with Redis setup instructions

### 2. Logging System
- Create app/utils/logger.py with structured logging
- Add log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Configure file rotation and formatting
- Integrate logging into all services and API endpoints
- Update .env with logging configuration

### 3. File Upload Security Validation
- Create app/utils/file_validator.py
- Implement MIME type validation
- Implement magic bytes verification
- Add file size limit enforcement
- Add virus scan placeholder
- Update books.py upload endpoint with validation

### 4. Database Connection Pooling
- Update app/core/database.py with connection pool configuration
- Add pool size settings to config.py
- Test connection reuse

### 5. Pagination
- Create app/utils/pagination.py with PaginatedResponse model
- Update books.py list endpoint with pagination
- Update reading.py endpoints with pagination
- Add pagination parameters to models

### 6. Rate Limiting
- Add slowapi to requirements.txt
- Create rate limiting middleware
- Configure rate limits per endpoint
- Add rate limit headers to responses

### 7. Background Task Queue (Celery)
- Add celery and redis to requirements.txt
- Create app/tasks/celery_app.py
- Create app/tasks/book_tasks.py for async book processing
- Update book_processing_service.py to use Celery
- Create Celery worker startup script
- Update docs with Celery setup instructions

### 8. Unit Tests Setup
- Add pytest, pytest-asyncio, pytest-cov to requirements.txt
- Create tests/ directory structure
- Create conftest.py with fixtures
- Write unit tests for:
  - SemanticSplitter
  - AuditService
  - TextExtractor
  - All providers (mocked)
- Add pytest configuration to pyproject.toml

### 9. Integration Tests Setup
- Create test database setup (separate Supabase project or test schema)
- Write integration tests for:
  - Book upload endpoint
  - Book list endpoint
  - Reading progress endpoints
  - Ambiance endpoint
- Add test data fixtures
- Add test coverage reporting
