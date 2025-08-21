# Web Crawler System Design Documentation

## Executive Summary

This document outlines the design for a scalable web crawler system capable of processing billions of URLs while maintaining high performance, reliability, and cost efficiency. The system is built using Django, Celery, PostgreSQL, and Redis, with Docker containerization for easy deployment and scaling.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                           │
└─────────────────┬───────────────────────────────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │      API Gateway          │
    └─────────────┬─────────────┘
                  │
    ┌─────────────┴─────────────┐
    │    Django Web Servers     │
    │    (Multiple Instances)   │
    └─────────────┬─────────────┘
                  │
    ┌─────────────┴─────────────┐
    │    Celery Workers         │
    │    (Scalable Pool)        │
    └─────────────┬─────────────┘
                  │
    ┌─────────────┴─────────────┐
    │    Redis Cluster          │
    │    (Message Broker)       │
    └─────────────┬─────────────┘
                  │
    ┌─────────────┴─────────────┐
    │   PostgreSQL Cluster      │
    │   (Primary + Replicas)    │
    └───────────────────────────┘
```

### Component Breakdown

1. **Load Balancer**: Distributes incoming requests across multiple web servers
2. **API Gateway**: Handles authentication, rate limiting, and request routing
3. **Django Web Servers**: Handle HTTP requests and API endpoints
4. **Celery Workers**: Process crawling tasks in parallel
5. **Redis Cluster**: Message broker and caching layer
6. **PostgreSQL Cluster**: Primary database with read replicas

## Data Schema Design

### Unified Data Schema

```sql
-- Websites table (partitioned by domain)
CREATE TABLE websites (
    id BIGSERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    robots_txt_url TEXT,
    robots_txt_content TEXT,
    crawl_delay INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crawled pages table (partitioned by date)
CREATE TABLE crawled_pages_YYYY_MM (
    id BIGSERIAL,
    url TEXT NOT NULL,
    website_id BIGINT REFERENCES websites(id),
    title VARCHAR(500),
    description TEXT,
    content TEXT,
    text_content TEXT,
    status_code INTEGER,
    content_type VARCHAR(100),
    content_length BIGINT,
    encoding VARCHAR(50),
    headers JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    topics JSONB DEFAULT '[]',
    category VARCHAR(100),
    sentiment VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    crawled_at TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Crawl jobs table
CREATE TABLE crawl_jobs (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    urls_file TEXT,
    urls_list JSONB,
    batch_size INTEGER DEFAULT 100,
    max_workers INTEGER DEFAULT 4,
    total_urls INTEGER DEFAULT 0,
    processed_urls INTEGER DEFAULT 0,
    successful_urls INTEGER DEFAULT 0,
    failed_urls INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    results_summary JSONB,
    error_log TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Topics table
CREATE TABLE topics (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    parent_topic_id BIGINT REFERENCES topics(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Page topics relationship
CREATE TABLE page_topics (
    id BIGSERIAL PRIMARY KEY,
    page_id BIGINT NOT NULL,
    topic_id BIGINT REFERENCES topics(id),
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Database Partitioning Strategy

1. **Time-based Partitioning**: Crawled pages partitioned by month
2. **Domain-based Partitioning**: Separate tables for high-traffic domains
3. **Archive Strategy**: Move old data to cheaper storage

## Scalability Design

### Horizontal Scaling

#### Web Servers
- **Auto-scaling**: Scale based on CPU/memory usage
- **Load balancing**: Round-robin with health checks
- **Session management**: Stateless design with Redis sessions

#### Celery Workers
- **Worker pools**: Separate pools for different task types
- **Queue management**: Priority queues for different URL types
- **Resource allocation**: CPU and memory limits per worker

#### Database Scaling
- **Read replicas**: Distribute read load
- **Connection pooling**: PgBouncer for connection management
- **Sharding**: Horizontal partitioning for large datasets

### Vertical Scaling

#### Resource Optimization
- **Memory management**: Efficient data structures
- **CPU optimization**: Async processing where possible
- **Storage optimization**: Compression and indexing

## Performance Optimization

### Caching Strategy

```python
# Multi-level caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    },
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/2',
    },
    'crawler': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/3',
        'TIMEOUT': 3600,  # 1 hour
    }
}
```

### Database Optimization

1. **Indexing Strategy**
   ```sql
   -- Composite indexes for common queries
   CREATE INDEX idx_pages_status_created ON crawled_pages(status, created_at);
   CREATE INDEX idx_pages_website_status ON crawled_pages(website_id, status);
   CREATE INDEX idx_pages_topics ON crawled_pages USING GIN(topics);
   ```

2. **Query Optimization**
   - Use database views for complex queries
   - Implement query result caching
   - Use database connection pooling

### Network Optimization

1. **Connection Pooling**: Reuse HTTP connections
2. **Compression**: Enable gzip compression
3. **CDN Integration**: Cache static content
4. **Rate Limiting**: Per-domain rate limiting

## Reliability Design

### Fault Tolerance

#### Service Redundancy
- **Multiple instances**: No single point of failure
- **Health checks**: Automatic failover
- **Circuit breakers**: Prevent cascade failures

#### Data Durability
- **Database replication**: Primary + multiple replicas
- **Backup strategy**: Automated daily backups
- **Disaster recovery**: Cross-region replication

### Error Handling

#### Retry Mechanisms
```python
@shared_task(bind=True, max_retries=3)
def crawl_single_url(self, url: str, job_id: int = None):
    try:
        # Crawling logic
        pass
    except Exception as exc:
        # Exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
```

#### Monitoring and Alerting
- **Application metrics**: Response times, error rates
- **Infrastructure metrics**: CPU, memory, disk usage
- **Business metrics**: URLs processed, success rates

## Cost Optimization

### Infrastructure Costs

#### Compute Optimization
- **Spot instances**: Use for non-critical workloads
- **Auto-scaling**: Scale down during low usage
- **Resource limits**: Set appropriate CPU/memory limits

#### Storage Optimization
- **Data lifecycle**: Archive old data to cheaper storage
- **Compression**: Compress stored content
- **Deduplication**: Avoid storing duplicate content

#### Network Optimization
- **CDN usage**: Reduce bandwidth costs
- **Compression**: Reduce data transfer
- **Caching**: Reduce redundant requests

### Operational Costs

#### Monitoring Costs
- **Log aggregation**: Centralized logging
- **Metrics collection**: Efficient metric storage
- **Alert management**: Reduce false positives

## Security Design

### Data Protection

#### Encryption
- **Data at rest**: Database encryption
- **Data in transit**: TLS/SSL encryption
- **API security**: JWT authentication

#### Access Control
- **Role-based access**: Different permission levels
- **API rate limiting**: Prevent abuse
- **Input validation**: Sanitize all inputs

### Compliance

#### GDPR Compliance
- **Data retention**: Configurable retention policies
- **Data deletion**: Right to be forgotten
- **Consent management**: Track user consent

#### Robots.txt Compliance
- **Respect robots.txt**: Honor website policies
- **Rate limiting**: Polite crawling
- **User agent identification**: Clear identification

## Monitoring and Observability

### Key Metrics

#### Application Metrics
- **Request rate**: Requests per second
- **Response time**: Average and 95th percentile
- **Error rate**: Percentage of failed requests
- **Success rate**: Percentage of successful crawls

#### Infrastructure Metrics
- **CPU usage**: Per service
- **Memory usage**: Per service
- **Disk usage**: Storage utilization
- **Network usage**: Bandwidth consumption

#### Business Metrics
- **URLs processed**: Total and per time period
- **Topics identified**: Classification accuracy
- **Job completion rate**: Success/failure rates
- **Data quality**: Content extraction success

### Monitoring Tools

#### Application Monitoring
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Jaeger**: Distributed tracing

#### Logging
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Fluentd**: Log aggregation
- **Splunk**: Log analysis

#### Alerting
- **PagerDuty**: Incident management
- **Slack**: Team notifications
- **Email**: Escalation alerts

## Service Level Objectives (SLOs)

### Availability SLOs
- **99.9% uptime**: System availability
- **< 200ms response time**: API response time
- **< 1% error rate**: Acceptable error rate

### Performance SLOs
- **1000 URLs/minute**: Processing capacity
- **< 5 seconds**: Job queue time
- **< 30 seconds**: URL processing time

### Quality SLOs
- **> 95% success rate**: Successful crawls
- **> 90% accuracy**: Topic classification
- **< 1% duplicate content**: Content deduplication

## Deployment Strategy

### Environment Strategy

#### Development Environment
- **Local development**: Docker Compose
- **Shared development**: Staging-like environment
- **Feature testing**: Isolated environments

#### Production Environment
- **Blue-green deployment**: Zero-downtime deployments
- **Canary releases**: Gradual rollout
- **Rollback strategy**: Quick rollback capability

### CI/CD Pipeline

#### Build Pipeline
1. **Code quality**: Linting and testing
2. **Security scanning**: Vulnerability assessment
3. **Performance testing**: Load testing
4. **Integration testing**: End-to-end testing

#### Deployment Pipeline
1. **Build artifacts**: Docker images
2. **Deploy to staging**: Automated testing
3. **Deploy to production**: Gradual rollout
4. **Monitor and validate**: Health checks

## Risk Assessment

### Technical Risks

#### High Risk
- **Database performance**: Large dataset handling
- **Network failures**: External service dependencies
- **Resource exhaustion**: Memory/CPU limits

#### Medium Risk
- **Third-party dependencies**: Library vulnerabilities
- **Data corruption**: Storage issues
- **Configuration errors**: Deployment issues

#### Low Risk
- **Code bugs**: Development issues
- **Documentation**: Knowledge transfer
- **Training**: Team skills

### Mitigation Strategies

#### High Risk Mitigation
- **Performance testing**: Regular load testing
- **Circuit breakers**: Fail-fast mechanisms
- **Resource monitoring**: Proactive monitoring

#### Medium Risk Mitigation
- **Dependency management**: Regular updates
- **Backup strategies**: Data protection
- **Configuration management**: Version control

## Success Metrics

### Technical Success Metrics
- **System uptime**: > 99.9%
- **Response time**: < 200ms average
- **Error rate**: < 1%
- **Throughput**: 1000 URLs/minute

### Business Success Metrics
- **URL processing**: Billions of URLs processed
- **Data quality**: High accuracy classification
- **Cost efficiency**: Low cost per URL
- **User satisfaction**: High API adoption

### Operational Success Metrics
- **Deployment frequency**: Daily deployments
- **Lead time**: < 1 hour from commit to production
- **Mean time to recovery**: < 1 hour
- **Change failure rate**: < 5%

## Conclusion

This design provides a comprehensive framework for building a scalable web crawler system capable of processing billions of URLs. The architecture prioritizes reliability, performance, and cost efficiency while maintaining flexibility for future enhancements.

The system is designed to be:
- **Scalable**: Handle billions of URLs through horizontal scaling
- **Reliable**: High availability with fault tolerance
- **Cost-effective**: Optimized resource usage
- **Maintainable**: Clear separation of concerns
- **Secure**: Comprehensive security measures
- **Observable**: Full monitoring and alerting

This design serves as a foundation for the proof of concept and can be iteratively improved. There are numerous other things that can be done (for example using Private Hosted Zone instead of Public). Can discuss other things that can be done over call / email.
