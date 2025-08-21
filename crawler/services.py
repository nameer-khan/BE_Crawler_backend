from typing import List, Dict, Optional, Any
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from urllib.parse import urlparse
import logging

from .models import Website, CrawledPage, CrawlJob, Topic, PageTopic

logger = logging.getLogger(__name__)

# New Relic integration for services
try:
    import newrelic.agent
except ImportError:
    newrelic = None


class WebsiteService:
    """Service for website-related database operations."""
    
    def get_website_by_domain(self, domain: str) -> Optional[Website]:
        """Get website by domain."""
        try:
            return Website.active_objects.get(domain=domain)
        except Website.DoesNotExist:
            return None
    
    def create_website(self, domain: str, name: str = None) -> Website:
        """Create a new website."""
        return Website.objects.create(domain=domain, name=name or domain)
    
    def get_or_create_website(self, domain: str) -> tuple[Website, bool]:
        """Get or create website by domain."""
        return Website.objects.get_or_create(domain=domain)
    
    def get_websites_with_stats(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get websites with crawling statistics."""
        websites = Website.active_objects.annotate(
            pages_count=Count('pages'),
            completed_pages=Count('pages', filter=Q(pages__crawl_status='completed')),
            failed_pages=Count('pages', filter=Q(pages__crawl_status='failed')),
            avg_content_length=Avg('pages__content_length')
        ).order_by('-pages_count')
        
        paginator = Paginator(websites, page_size)
        websites_page = paginator.get_page(page)
        
        return {
            'websites': websites_page,
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page
        }


class CrawledPageService:
    """Service for crawled page-related database operations."""
    
    def get_page_by_url(self, url: str) -> Optional[CrawledPage]:
        """Get crawled page by URL."""
        try:
            return CrawledPage.active_objects.get(url=url)
        except CrawledPage.DoesNotExist:
            return None
    
    def get_page_by_id(self, page_id: int) -> Optional[CrawledPage]:
        """Get crawled page by ID."""
        try:
            return CrawledPage.active_objects.get(id=page_id)
        except CrawledPage.DoesNotExist:
            return None
    
    def create_page(self, url: str, website: Website, **kwargs) -> CrawledPage:
        """Create a new crawled page."""
        return CrawledPage.objects.create(url=url, website=website, **kwargs)
    
    def get_or_create_page(self, url: str, website: Website, **kwargs) -> tuple[CrawledPage, bool]:
        """Get or create crawled page."""
        return CrawledPage.objects.get_or_create(
            url=url,
            defaults={'website': website, **kwargs}
        )
    
    def update_page_status(self, page_id: int, status: str, **kwargs) -> CrawledPage:
        """Update page status and other fields."""
        page = CrawledPage.objects.get(id=page_id)
        for field, value in kwargs.items():
            setattr(page, field, value)
        page.crawl_status = status
        page.save()
        return page
    
    def get_pages_with_filters(self, filters: Dict[str, Any] = None, 
                              page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get pages with optional filters and pagination."""
        queryset = CrawledPage.active_objects.select_related('website').all()
        
        if filters:
            if filters.get('status'):
                queryset = queryset.filter(crawl_status=filters['status'])
            if filters.get('website_id'):
                queryset = queryset.filter(website_id=filters['website_id'])
            if filters.get('category'):
                # Filter by topics (category is actually a topic)
                queryset = queryset.filter(topics__contains=[filters['category']])
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])
            if filters.get('search'):
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(url__icontains=search_term)
                )
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        paginator = Paginator(queryset, page_size)
        pages_page = paginator.get_page(page)
        
        return {
            'pages': pages_page,
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page
        }
    
    def get_pages_by_website(self, website_id: int, page: int = 1, 
                           page_size: int = 20) -> Dict[str, Any]:
        """Get pages for a specific website."""
        queryset = CrawledPage.active_objects.filter(website_id=website_id).order_by('-created_at')
        
        paginator = Paginator(queryset, page_size)
        pages_page = paginator.get_page(page)
        
        return {
            'pages': pages_page,
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page
        }
    
    def get_pages_by_topic(self, topic: str, page: int = 1, 
                          page_size: int = 20) -> Dict[str, Any]:
        """Get pages that contain a specific topic."""
        queryset = CrawledPage.active_objects.filter(topics__contains=[topic]).order_by('-created_at')
        
        paginator = Paginator(queryset, page_size)
        pages_page = paginator.get_page(page)
        
        return {
            'pages': pages_page,
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page
        }
    
    def recrawl_page(self, page_id: int) -> CrawledPage:
        """Mark a page for recrawling."""
        page = CrawledPage.objects.get(id=page_id)
        page.crawl_status = 'pending'
        page.retry_count = 0
        page.error_message = ''
        page.save(update_fields=['crawl_status', 'retry_count', 'error_message'])
        return page
    
    def get_crawling_stats(self) -> Dict[str, Any]:
        """Get crawling statistics."""
        total_pages = CrawledPage.active_objects.count()
        completed_pages = CrawledPage.active_objects.filter(crawl_status='completed').count()
        failed_pages = CrawledPage.active_objects.filter(crawl_status='failed').count()
        pending_pages = CrawledPage.active_objects.filter(crawl_status='pending').count()
        crawling_pages = CrawledPage.active_objects.filter(crawl_status='crawling').count()
        
        # Average content length for completed pages
        avg_content_length = CrawledPage.active_objects.filter(
            crawl_status='completed', 
            content_length__isnull=False
        ).aggregate(avg_length=Avg('content_length'))['avg_length'] or 0
        
        # Pages crawled in last 24 hours
        last_24h = timezone.now() - timezone.timedelta(hours=24)
        pages_last_24h = CrawledPage.active_objects.filter(
            crawled_at__gte=last_24h
        ).count()
        
        return {
            'total_pages': total_pages,
            'completed_pages': completed_pages,
            'failed_pages': failed_pages,
            'pending_pages': pending_pages,
            'crawling_pages': crawling_pages,
            'success_rate': (completed_pages / total_pages * 100) if total_pages > 0 else 0,
            'avg_content_length': avg_content_length,
            'pages_last_24h': pages_last_24h
        }


class CrawlJobService:
    """Service for crawl job-related database operations."""
    
    def create_job(self, name: str, urls: List[str], **kwargs) -> CrawlJob:
        """Create a new crawl job."""
        return CrawlJob.objects.create(
            name=name,
            total_urls=len(urls),
            urls_list=urls,  # Store the URLs list
            **kwargs
        )
    
    def get_job_by_id(self, job_id: int) -> Optional[CrawlJob]:
        """Get crawl job by ID."""
        try:
            return CrawlJob.active_objects.get(id=job_id)
        except CrawlJob.DoesNotExist:
            return None
    
    def update_job_progress(self, job_id: int, completed_count: int = None, 
                          failed_count: int = None, status: str = None) -> CrawlJob:
        """Update job progress."""
        job = CrawlJob.objects.get(id=job_id)
        
        if completed_count is not None:
            job.completed_urls = completed_count
        if failed_count is not None:
            job.failed_urls = failed_count
        if status:
            job.job_status = status
        
        # Calculate progress percentage
        if job.total_urls > 0:
            job.progress = ((job.completed_urls + job.failed_urls) / job.total_urls) * 100
        
        job.save()
        return job
    
    def get_jobs_with_pagination(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get crawl jobs with pagination."""
        queryset = CrawlJob.active_objects.all().order_by('-created_at')
        
        paginator = Paginator(queryset, page_size)
        jobs_page = paginator.get_page(page)
        
        return {
            'jobs': jobs_page,
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page
        }
    
    def cancel_job(self, job_id: int) -> CrawlJob:
        """Cancel a crawl job."""
        job = CrawlJob.objects.get(id=job_id)
        job.job_status = 'cancelled'
        job.save(update_fields=['job_status'])
        return job


class TopicService:
    """Service for topic-related database operations."""
    
    def get_all_topics(self) -> List[Topic]:
        """Get all topics."""
        return Topic.active_objects.all().order_by('name')
    
    def get_topic_by_name(self, name: str) -> Optional[Topic]:
        """Get topic by name."""
        try:
            return Topic.active_objects.get(name=name)
        except Topic.DoesNotExist:
            return None
    
    def create_topic(self, name: str) -> Topic:
        """Create a new topic."""
        from django.utils.text import slugify
        topic_slug = slugify(name)
        return Topic.objects.create(name=name, slug=topic_slug)
    
    def get_or_create_topic(self, name: str) -> tuple[Topic, bool]:
        """Get or create topic."""
        from django.utils.text import slugify
        topic_slug = slugify(name)
        return Topic.objects.get_or_create(name=name, defaults={'slug': topic_slug})
    
    def get_topics_with_page_counts(self) -> List[Dict[str, Any]]:
        """Get topics with page counts."""
        topics = Topic.active_objects.annotate(
            actual_page_count=Count('page_topics')
        ).order_by('-actual_page_count')
        
        return [
            {
                'id': topic.id,
                'name': topic.name,
                'slug': topic.slug,
                'page_count': topic.actual_page_count
            }
            for topic in topics
        ]


class CrawlerDatabaseService:
    """Main service for crawler database operations."""
    
    def __init__(self):
        self.website_service = WebsiteService()
        self.page_service = CrawledPageService()
        self.job_service = CrawlJobService()
        self.topic_service = TopicService()
    
    def process_single_url(self, url: str) -> Dict[str, Any]:
        """Process a single URL for crawling."""
        # New Relic custom attributes
        if newrelic:
            newrelic.agent.add_custom_attribute('service_method', 'process_single_url')
            newrelic.agent.add_custom_attribute('url', url)
        
        try:
            domain = urlparse(url).netloc
            website, created = self.website_service.get_or_create_website(domain)
            
            page, created = self.page_service.get_or_create_page(
                url=url,
                website=website,
                crawl_status='pending'
            )
            
            return {
                'page_id': page.id,
                'website_id': website.id,
                'created': created,
                'current_status': page.crawl_status
            }
        except Exception as e:
            logger.error(f"Error processing URL {url}: {str(e)}")
            if newrelic:
                newrelic.agent.record_exception(e)
            raise
    
    def process_bulk_urls(self, urls: List[str], job_name: str = None) -> Dict[str, Any]:
        """Process multiple URLs for crawling."""
        # New Relic custom attributes
        if newrelic:
            newrelic.agent.add_custom_attribute('service_method', 'process_bulk_urls')
            newrelic.agent.add_custom_attribute('url_count', len(urls))
            newrelic.agent.add_custom_attribute('job_name', job_name)
        
        try:
            if not job_name:
                job_name = f"Bulk crawl {len(urls)} URLs - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Create crawl job
            job = self.job_service.create_job(name=job_name, urls=urls)
            
            # Process each URL
            processed_urls = []
            for url in urls:
                result = self.process_single_url(url)
                processed_urls.append(result)
            
            return {
                'job_id': job.id,
                'job_name': job.name,
                'total_urls': len(urls),
                'processed_urls': processed_urls
            }
        except Exception as e:
            logger.error(f"Error processing bulk URLs: {str(e)}")
            if newrelic:
                newrelic.agent.record_exception(e)
            raise
    
    def get_crawler_stats(self) -> Dict[str, Any]:
        """Get comprehensive crawler statistics."""
        # New Relic custom attributes
        if newrelic:
            newrelic.agent.add_custom_attribute('service_method', 'get_crawler_stats')
        
        try:
            page_stats = self.page_service.get_crawling_stats()
            
            # Website stats
            total_websites = Website.active_objects.count()
            active_websites = Website.active_objects.filter(
                pages__crawl_status='completed'
            ).distinct().count()
            
            # Job stats
            total_jobs = CrawlJob.active_objects.count()
            active_jobs = CrawlJob.active_objects.filter(job_status='running').count()
            completed_jobs = CrawlJob.active_objects.filter(job_status='completed').count()
            
            # Topic stats
            total_topics = Topic.active_objects.count()
            
            return {
                'pages': page_stats,
                'websites': {
                    'total': total_websites,
                    'active': active_websites
                },
                'jobs': {
                    'total': total_jobs,
                    'active': active_jobs,
                    'completed': completed_jobs
                },
                'topics': {
                    'total': total_topics
                }
            }
        except Exception as e:
            logger.error(f"Error getting crawler stats: {str(e)}")
            if newrelic:
                newrelic.agent.record_exception(e)
            raise
