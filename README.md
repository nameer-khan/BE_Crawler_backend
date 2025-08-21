# Web Crawler and Content Classification System

A Django-based web crawler system that can crawl URLs, extract content, and classify pages into relevant topics. Built with scalability in mind to handle billions of URLs.

## Features

- **Core Crawler**: Extract metadata and content from any URL
- **Topic Classification**: Automatically classify pages into relevant topics
- **REST API**: Full API for crawling operations with comprehensive documentation
- **API Documentation**: Interactive Swagger UI and ReDoc documentation
- **Background Processing**: Celery-based task queue for scalable processing
- **Database Storage**: PostgreSQL for storing crawled data and metadata
- **Docker Support**: Complete containerization for easy deployment
- **Admin Interface**: Django admin for monitoring and management
- **Monitoring**: New Relic integration for performance monitoring and error tracking
- **Robots.txt Compliance**: Respects robots.txt files
- **Rate Limiting**: Configurable delays between requests
- **Error Handling**: Robust error handling and retry mechanisms

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django Web    │    │   Celery        │    │   PostgreSQL    │
│   Application   │◄──►│   Workers       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Cache   │    │   Web Crawler   │    │   Content       │
│   & Message     │    │   Engine        │    │   Classifier    │
│   Broker        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Brightedge-SEO
   ```

2. **Start the services (First time load might take a few minutes)**
   ```bash
   docker-compose up -d
   ```

3. **Run database migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Create a superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

5. **Access the application**
   - Web Application: http://localhost:8000
   - Admin Interface: http://localhost:8000/admin
   - API Documentation: http://localhost:8000/api/
   - Swagger UI: http://localhost:8000/api/docs/
   - ReDoc: http://localhost:8000/api/redoc/
   - OpenAPI Schema: http://localhost:8000/api/schema/

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

4. **Start the development server**
   ```bash
   python manage.py runserver
   ```

5. **Start Celery worker (in another terminal)**
   ```bash
   celery -A webcrawler worker -l info
   ```

## API Usage

### Single URL Crawling

```bash
curl -X POST http://localhost:8000/api/crawler/crawl_url/ \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.amazon.com/Cuisinart-CPT-122-Compact-2-Slice-Toaster/dp/B009GQ034C/",
    "extract_content": true,
    "classify_topics": true,
    "respect_robots_txt": true
  }'
```

### Bulk URL Crawling

```bash
curl -X POST http://localhost:8000/api/crawler/crawl_bulk/ \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.amazon.com/Cuisinart-CPT-122-Compact-2-Slice-Toaster/dp/B009GQ034C/",
      "https://blog.rei.com/camp/how-to-introduce-your-indoorsy-friend-to-the-outdoors/",
      "https://www.cnn.com/2013/06/10/politics/edward-snowden-profile/"
    ],
    "batch_size": 10
  }'
```

### Upload URLs from File

```bash
curl -X POST http://localhost:8000/api/crawler/crawl_from_file/ \
  -F "file=@urls.txt"
```

### Get Crawling Statistics

```bash
curl http://localhost:8000/api/crawler/stats/
```

## API Endpoints

### Core Crawler Endpoints

- `POST /api/crawler/crawl_url/` - Crawl a single URL
- `POST /api/crawler/crawl_bulk/` - Crawl multiple URLs
- `POST /api/crawler/crawl_from_file/` - Crawl URLs from uploaded file
- `GET /api/crawler/stats/` - Get crawling statistics

### Data Management Endpoints

- `GET /api/pages/` - List crawled pages
- `GET /api/pages/{id}/` - Get specific page details
- `POST /api/pages/{id}/recrawl/` - Recrawl a page
- `POST /api/pages/{id}/classify_topics/` - Reclassify topics

- `GET /api/jobs/` - List crawl jobs
- `GET /api/jobs/{id}/` - Get job details
- `POST /api/jobs/{id}/start/` - Start a job
- `POST /api/jobs/{id}/cancel/` - Cancel a job
- `GET /api/jobs/{id}/status/` - Get job status

- `GET /api/websites/` - List websites
- `GET /api/topics/` - List topics

## Testing the System

### Test URLs

The system has been tested with the following URLs:

1. **Amazon Product Page**
   ```
   http://www.amazon.com/Cuisinart-CPT-122-Compact-2-Slice-Toaster/dp/B009GQ034C/
   ```
   Expected topics: `['automotive', 'food', 'technology']`

2. **REI Blog Post**
   ```
   https://blog.rei.com/camp/how-to-introduce-your-indoorsy-friend-to-the-outdoors/
   ```
   Expected topics: `['travel', 'sports', 'education']`

3. **CNN News Article**
   ```
   https://www.cnn.com/2013/06/10/politics/edward-snowden-profile/
   ```
   Expected topics: `['politics', 'technology', 'business']`

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test
python manage.py test crawler.tests.test_crawler
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=webcrawler
POSTGRES_USER=webcrawler
POSTGRES_PASSWORD=webcrawler123
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# New Relic
NEW_RELIC_CONFIG_FILE=/app/newrelic.ini
NEW_RELIC_ENVIRONMENT=development

# Crawler Settings
CRAWLER_USER_AGENT=WebCrawler/1.0 (+https://github.com/your-repo)
CRAWLER_REQUEST_TIMEOUT=30
CRAWLER_MAX_RETRIES=3
CRAWLER_DELAY_BETWEEN_REQUESTS=1
CRAWLER_RESPECT_ROBOTS_TXT=True
CRAWLER_MAX_CONTENT_LENGTH=10485760
```

### Crawler Settings

The crawler behavior can be configured in `settings.py`:

```python
CRAWLER_SETTINGS = {
    'USER_AGENT': 'WebCrawler/1.0 (+https://github.com/your-repo)',
    'REQUEST_TIMEOUT': 30,
    'MAX_RETRIES': 3,
    'DELAY_BETWEEN_REQUESTS': 1,  # seconds
    'RESPECT_ROBOTS_TXT': True,
    'MAX_CONTENT_LENGTH': 10 * 1024 * 1024,  # 10MB
}
```

## Database Schema

### Core Tables

- **websites**: Domain information and robots.txt data
- **crawled_pages**: All crawled page data and metadata
- **crawl_jobs**: Job tracking and progress
- **topics**: Topic classifications
- **page_topics**: Many-to-many relationship with confidence scores

### Key Fields

- **crawled_pages**: URL, title, description, content, topics, status
- **crawl_jobs**: Progress tracking, success/failure counts
- **page_topics**: Confidence scores for topic classification

## Monitoring and Logging

### Logs

Logs are available in the Docker containers:

```bash
# Web application logs
docker-compose logs web

# Celery worker logs
docker-compose logs celery

# Database logs
docker-compose logs db
```

### Health Checks

The system includes health checks for all services:

```bash
# Check service health
docker-compose ps
```

### New Relic Monitoring

The application includes comprehensive New Relic monitoring:

- **Performance Monitoring**: Track response times, throughput, and error rates
- **Error Tracking**: Automatic error detection and reporting
- **Custom Attributes**: Detailed metrics for crawler operations
- **Distributed Tracing**: Track requests across services
- **Custom Dashboards**: Monitor crawler-specific metrics

To view monitoring data:
1. Access your New Relic dashboard
2. Look for the "Bright-Web-Crawler" application
3. Monitor key metrics like:
   - Crawl success/failure rates
   - Processing times
   - Topic classification accuracy
   - Database performance
   - Celery task performance

## Scaling Considerations

### For Billions of URLs

1. **Database Optimization**
   - Partition tables by date
   - Use read replicas
   - Implement caching layers

2. **Worker Scaling**
   - Scale Celery workers horizontally
   - Use multiple Redis instances
   - Implement job queuing strategies

3. **Storage**
   - Use object storage for content
   - Implement data archival
   - Compress stored data

4. **Rate Limiting**
   - Per-domain rate limiting
   - Respect robots.txt
   - Implement polite crawling

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

2. **Celery Worker Not Starting**
   ```bash
   docker-compose restart celery
   ```

3. **Memory Issues**
   - Increase Docker memory limits
   - Reduce batch sizes
   - Implement data cleanup

### Debug Mode

Enable debug mode for detailed error messages:

```python
DEBUG = True
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
