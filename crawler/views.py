"""
Django REST Framework views for the crawler app.
"""

import time
import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from urllib.parse import urlparse

from .models import Website, CrawledPage, CrawlJob, Topic, PageTopic
from .serializers import (
    WebsiteSerializer, CrawledPageSerializer, CrawledPageListSerializer,
    CrawlJobSerializer, CrawlJobCreateSerializer, TopicSerializer,
    URLProcessRequestSerializer, URLProcessResponseSerializer,
    BulkURLProcessRequestSerializer, CrawlJobStatusSerializer
)
from .crawler import WebCrawler
from .tasks import crawl_single_url, crawl_bulk_urls, classify_page_topics
from .services import CrawlerDatabaseService

logger = logging.getLogger(__name__)

# New Relic integration for views
try:
    import newrelic.agent
except ImportError:
    newrelic = None


from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

@extend_schema(
    tags=['API Root'],
    summary='API Root',
    description='API root endpoint providing links to all available endpoints.',
    responses={200: None}
)
@api_view(['GET'])
def api_root(request, format=None):
    """
    API root endpoint providing links to all available endpoints.
    """
    return Response({
        'message': 'Web Crawler API',
        'description': 'A Django-based web crawler system that can crawl URLs, extract content, and classify pages into relevant topics.',
        'version': '1.0.0',
        'documentation': {
            'swagger': reverse('swagger-ui', request=request, format=format),
            'redoc': reverse('redoc', request=request, format=format),
            'schema': reverse('schema', request=request, format=format),
        },
        'endpoints': {
            'websites': reverse('websites', request=request, format=format),
            'pages': reverse('pages', request=request, format=format),
            'jobs': reverse('jobs', request=request, format=format),
            'topics': reverse('topics', request=request, format=format),
            'crawler': {
                'crawl_url': reverse('crawl-url', request=request, format=format),
                'crawl_bulk': reverse('crawl-bulk', request=request, format=format),
                'crawl_from_file': reverse('crawl-from-file', request=request, format=format),
                'stats': reverse('crawler-stats', request=request, format=format),
            }
        }
    })


@extend_schema(tags=['Websites'])
class WebsiteAPIView(APIView):
    """
    API view for Website operations.

    Provides endpoints to retrieve website information with crawling statistics.
    """

    def get(self, request, *args, **kwargs):
        """
        Get websites with statistics and pagination.

        Returns a list of websites with their crawling statistics including
        total pages crawled, success/failure counts, and pagination information.

        Query Parameters:
        - page: Page number for pagination (default: 1)
        - page_size: Number of items per page (default: 20)
        """
        website_service = CrawlerDatabaseService().website_service
        
        # Get query parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Get websites with stats
        result = website_service.get_websites_with_stats(page=page, page_size=page_size)
        
        # Serialize the data
        serializer = WebsiteSerializer(result['websites'], many=True)
        
        response_data = {
            'websites': serializer.data,
            'pagination': {
                'total_count': result['total_count'],
                'total_pages': result['total_pages'],
                'current_page': result['current_page'],
                'page_size': page_size
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class CrawledPageAPIView(APIView):
    """API view for CrawledPage operations."""
    
    def get(self, request, *args, **kwargs):
        """Get crawled pages with filters and pagination."""
        page_service = CrawlerDatabaseService().page_service
        
        # Get query parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Build filters from query parameters
        filters = {}
        if request.query_params.get('status'):
            filters['status'] = request.query_params.get('status')
        if request.query_params.get('website_id'):
            filters['website_id'] = int(request.query_params.get('website_id'))
        if request.query_params.get('category'):
            filters['category'] = request.query_params.get('category')
        if request.query_params.get('search'):
            filters['search'] = request.query_params.get('search')
        
        # Get pages with filters
        result = page_service.get_pages_with_filters(
            filters=filters, 
            page=page, 
            page_size=page_size
        )
        
        # Serialize the data
        serializer = CrawledPageListSerializer(result['pages'], many=True)
        
        response_data = {
            'pages': serializer.data,
            'pagination': {
                'total_count': result['total_count'],
                'total_pages': result['total_pages'],
                'current_page': result['current_page'],
                'page_size': page_size
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class CrawledPageDetailAPIView(APIView):
    """API view for individual CrawledPage operations."""
    
    def get(self, request, page_id, *args, **kwargs):
        """Get a specific crawled page by ID."""
        page_service = CrawlerDatabaseService().page_service
        
        page = page_service.get_page_by_id(page_id)
        
        if not page:
            return Response({
                'error': 'Page not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CrawledPageSerializer(page)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, page_id, *args, **kwargs):
        """Recrawl a specific page."""
        page_service = CrawlerDatabaseService().page_service
        
        # Get page by ID
        page = page_service.get_page_by_id(page_id)
        
        if not page:
            return Response({
                'error': 'Page not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update page status for recrawling
        page = page_service.update_page_status(
            page_id=page_id,
            status='pending',
            error_message='',
            retry_count=0
        )
        
        # Schedule crawling task
        crawl_single_url.delay(page.url)
        
        return Response({
            'message': f'Recrawl scheduled for {page.url}',
            'page_id': page.id
        })


class CrawledPageTopicsAPIView(APIView):
    """API view for CrawledPage topic classification."""
    
    def post(self, request, page_id, *args, **kwargs):
        """Manually classify topics for a page."""
        page_service = CrawlerDatabaseService().page_service
        
        # Get page by ID
        page = page_service.get_page_by_id(page_id)
        
        if not page:
            return Response({
                'error': 'Page not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Schedule topic classification
        classify_page_topics.delay(page.id)
        
        return Response({
            'message': f'Topic classification scheduled for page {page.id}',
            'page_id': page.id
        })


class CrawlJobAPIView(APIView):
    """API view for CrawlJob operations."""
    
    def get(self, request, *args, **kwargs):
        """Get crawl jobs with pagination."""
        job_service = CrawlerDatabaseService().job_service
        
        # Get query parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Get jobs with pagination
        result = job_service.get_jobs_with_pagination(page=page, page_size=page_size)
        
        # Serialize the data
        serializer = CrawlJobSerializer(result['jobs'], many=True)
        
        response_data = {
            'jobs': serializer.data,
            'pagination': {
                'total_count': result['total_count'],
                'total_pages': result['total_pages'],
                'current_page': result['current_page'],
                'page_size': page_size
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        """Create a new crawl job."""
        serializer = CrawlJobCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create job through service
        job_service = CrawlerDatabaseService().job_service
        job_data = serializer.validated_data
        
        # Create the job
        job = job_service.create_job(
            name=job_data['name'],
            urls=job_data.get('urls_list', []),
            description=job_data.get('description', ''),
            batch_size=job_data.get('batch_size', 10)
        )
        
        response_serializer = CrawlJobSerializer(job)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CrawlJobDetailAPIView(APIView):
    """API view for individual CrawlJob operations."""
    
    def get(self, request, job_id, *args, **kwargs):
        """Get a specific crawl job by ID."""
        job_service = CrawlerDatabaseService().job_service
        
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            return Response({
                'error': 'Job not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CrawlJobSerializer(job)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, job_id, *args, **kwargs):
        """Start a crawl job."""
        job_service = CrawlerDatabaseService().job_service
        
        # Get job by ID
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            return Response({
                'error': 'Job not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if job.status != 'pending':
            return Response({
                'error': f'Job is already {job.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get URLs from job
        urls = []
        if job.urls_list:
            urls = job.urls_list
        elif job.urls_file:
            # Read URLs from file
            try:
                with job.urls_file.open('r') as f:
                    urls = [line.strip() for line in f if line.strip()]
            except Exception as e:
                return Response({
                    'error': f'Error reading URLs file: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if not urls:
            return Response({
                'error': 'No URLs found in job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Start bulk crawling
        crawl_bulk_urls.delay(urls, job.id)
        
        return Response({
            'message': f'Started crawling {len(urls)} URLs',
            'job_id': job.id,
            'total_urls': len(urls)
        })


class CrawlJobCancelAPIView(APIView):
    """API view for cancelling crawl jobs."""
    
    def post(self, request, job_id, *args, **kwargs):
        """Cancel a crawl job."""
        job_service = CrawlerDatabaseService().job_service
        
        # Get job by ID
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            return Response({
                'error': 'Job not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if job.status not in ['pending', 'running']:
            return Response({
                'error': f'Cannot cancel job in {job.status} status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancel the job
        job = job_service.cancel_job(job_id)
        
        return Response({
            'message': 'Job cancelled successfully',
            'job_id': job.id
        })


class CrawlJobStatusAPIView(APIView):
    """API view for crawl job status."""
    
    def get(self, request, job_id, *args, **kwargs):
        """Get detailed status of a crawl job."""
        job_service = CrawlerDatabaseService().job_service
        
        # Get job by ID
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            return Response({
                'error': 'Job not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CrawlJobStatusSerializer({
            'job_id': job.id,
            'name': job.name,
            'status': job.status,
            'progress_percentage': job.get_progress_percentage(),
            'total_urls': job.total_urls,
            'processed_urls': job.processed_urls,
            'successful_urls': job.successful_urls,
            'failed_urls': job.failed_urls,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'estimated_completion': None  # TODO: Calculate based on progress
        })
        
        return Response(serializer.data)


class TopicAPIView(APIView):
    """API view for Topic operations."""
    
    def get(self, request, *args, **kwargs):
        """Get topics with page counts."""
        topic_service = CrawlerDatabaseService().topic_service
        
        # Get topics with page counts
        topics_data = topic_service.get_topics_with_page_counts()
        
        # Serialize the data
        serializer = TopicSerializer(topics_data, many=True)
        
        response_data = {
            'topics': serializer.data,
            'total_count': len(topics_data)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=['Crawler Operations'])
class CrawlURLAPIView(APIView):
    """
    API view for crawling a single URL.

    Provides endpoint to crawl a single URL and return immediate results.
    """

    def post(self, request, *args, **kwargs):
        """
        Crawl a single URL and return results.

        Crawls the specified URL and returns extracted content, metadata,
        and topic classification if requested.

        Request Body:
        - url: The URL to crawl (required)
        - extract_content: Whether to extract page content (default: true)
        - classify_topics: Whether to classify topics (default: true)
        - respect_robots_txt: Whether to respect robots.txt (default: true)
        """
        serializer = URLProcessRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        url = data['url']
        extract_content = data['extract_content']
        classify_topics = data['classify_topics']
        respect_robots_txt = data['respect_robots_txt']
        
        # New Relic custom attributes
        if newrelic:
            newrelic.agent.add_custom_attribute('url', url)
            newrelic.agent.add_custom_attribute('extract_content', extract_content)
            newrelic.agent.add_custom_attribute('classify_topics', classify_topics)
            newrelic.agent.add_custom_attribute('respect_robots_txt', respect_robots_txt)

        start_time = time.time()
        
        try:
            # Process URL through service layer
            crawler_service = CrawlerDatabaseService()
            result = crawler_service.process_single_url(url)
            
            # Crawl the URL
            crawler = WebCrawler(respect_robots_txt=respect_robots_txt)
            crawl_result = crawler.crawl_url(url)
            
            # Ensure crawl_result has all required fields
            if not isinstance(crawl_result, dict):
                raise ValueError(f"Invalid crawl result format: {type(crawl_result)}")
            
            # Set default values for missing fields
            crawl_result.setdefault('title', None)
            crawl_result.setdefault('description', None)
            crawl_result.setdefault('content', None)
            crawl_result.setdefault('text_content', None)
            crawl_result.setdefault('topics', [])
            crawl_result.setdefault('status_code', None)
            crawl_result.setdefault('content_type', None)
            crawl_result.setdefault('content_length', None)
            crawl_result.setdefault('encoding', None)
            crawl_result.setdefault('headers', {})
            crawl_result.setdefault('error_message', None)
            
            # Save to database if successful
            if crawl_result['status'] == 'completed':
                page_service = crawler_service.page_service
                page = page_service.get_page_by_id(result['page_id'])
                
                if page:
                    try:
                        page_service.update_page_status(
                            page_id=page.id,
                            status=crawl_result['status'],
                            title=crawl_result['title'],
                            description=crawl_result['description'],
                            content=crawl_result['content'] if extract_content else None,
                            text_content=crawl_result['text_content'] if extract_content else None,
                            status_code=crawl_result['status_code'],
                            content_type=crawl_result['content_type'],
                            content_length=crawl_result['content_length'],
                            encoding=crawl_result['encoding'],
                            headers=crawl_result['headers'],
                            topics=crawl_result['topics'] if classify_topics else [],
                            crawled_at=timezone.now()
                        )
                    except Exception as db_error:
                        logger.error(f"Error saving to database: {str(db_error)}")
                        # Continue with response even if database save fails
            
            # Prepare response
            response_data = {
                'url': url,
                'status': crawl_result['status'],
                'title': crawl_result['title'],
                'description': crawl_result['description'],
                'content_preview': crawl_result['text_content'][:500] if crawl_result['text_content'] else None,
                'topics': crawl_result['topics'] if classify_topics else [],
                'status_code': crawl_result['status_code'],
                'content_type': crawl_result['content_type'],
                'content_length': crawl_result['content_length'],
                'error_message': crawl_result['error_message'],
                'processing_time': time.time() - start_time,
                'crawled_at': timezone.now()
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return Response({
                'url': url,
                'status': 'failed',
                'error_message': str(e),
                'processing_time': time.time() - start_time,
                'crawled_at': timezone.now()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=['Crawler Operations'])
class CrawlBulkAPIView(APIView):
    """API view for bulk crawling operations."""
    
    def post(self, request, *args, **kwargs):
        """Crawl multiple URLs in bulk."""
        serializer = BulkURLProcessRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        urls = data['urls']
        batch_size = data['batch_size']
        
        # New Relic custom attributes
        if newrelic:
            newrelic.agent.add_custom_attribute('url_count', len(urls))
            newrelic.agent.add_custom_attribute('batch_size', batch_size)

        try:
            # Process bulk URLs through service layer
            crawler_service = CrawlerDatabaseService()
            result = crawler_service.process_bulk_urls(urls)
            
            # Get classification parameters from request
            classify_topics = data.get('classify_topics', True)
            extract_content = data.get('extract_content', True)
            respect_robots_txt = data.get('respect_robots_txt', True)

            # Try to start bulk crawling with Celery
            try:
                crawl_bulk_urls.delay(urls, result['job_id'], classify_topics, extract_content, respect_robots_txt)
                return Response({
                    'message': f'Bulk crawl started for {len(urls)} URLs',
                    'job_id': result['job_id'],
                    'total_urls': len(urls),
                    'batch_size': batch_size,
                    'classify_topics': classify_topics,
                    'extract_content': extract_content,
                    'respect_robots_txt': respect_robots_txt,
                    'status': 'queued'
                })
            except Exception as celery_error:
                logger.error(f"Celery connection error: {str(celery_error)}")
                return Response({
                    'message': f'Bulk crawl job created but Celery is not available. URLs will be processed when Celery is ready.',
                    'job_id': result['job_id'],
                    'total_urls': len(urls),
                    'batch_size': batch_size,
                    'classify_topics': classify_topics,
                    'extract_content': extract_content,
                    'respect_robots_txt': respect_robots_txt,
                    'status': 'created_but_not_queued',
                    'celery_error': str(celery_error)
                }, status=status.HTTP_202_ACCEPTED)
                
        except Exception as e:
            logger.error(f"Error in bulk crawling: {str(e)}")
            return Response({
                'error': f'Error processing bulk URLs: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CrawlFromFileAPIView(APIView):
    """API view for crawling URLs from uploaded file."""
    
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        """Crawl URLs from uploaded file."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Read URLs from file
            urls = []
            for line in file_obj:
                url = line.decode('utf-8').strip()
                if url:
                    urls.append(url)
            
            if not urls:
                return Response({
                    'error': 'No valid URLs found in file'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process bulk URLs through service layer
            crawler_service = CrawlerDatabaseService()
            job_name = f"File crawl - {file_obj.name}"
            result = crawler_service.process_bulk_urls(urls, job_name)
            
            # Start bulk crawling with default classification parameters
            crawl_bulk_urls.delay(urls, result['job_id'], True, True, True)

            return Response({
                'message': f'File crawl started for {len(urls)} URLs',
                'job_id': result['job_id'],
                'total_urls': len(urls),
                'filename': file_obj.name
            })
            
        except Exception as e:
            return Response({
                'error': f'Error processing file: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Crawler Operations'])
class CrawlerStatsAPIView(APIView):
    """API view for crawling statistics."""
    
    def get(self, request, *args, **kwargs):
        """Get crawling statistics."""
        # New Relic custom attributes
        if newrelic:
            newrelic.agent.add_custom_attribute('endpoint', 'crawler_stats')

        crawler_service = CrawlerDatabaseService()
        stats = crawler_service.get_crawler_stats()
        
        return Response(stats)
