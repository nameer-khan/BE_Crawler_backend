"""
Celery tasks for background processing.
"""

import logging
from celery import shared_task
from django.utils import timezone
from urllib.parse import urlparse
from .models import Website, CrawledPage, CrawlJob, Topic, PageTopic
from .crawler import WebCrawler

logger = logging.getLogger(__name__)

# New Relic integration for tasks
try:
    import newrelic.agent
except ImportError:
    newrelic = None


@shared_task(bind=True, max_retries=3)
def crawl_single_url(self, url: str, job_id: int = None):
    """
    Crawl a single URL and store results.
    
    Args:
        url: URL to crawl
        job_id: Optional crawl job ID for tracking
    """
    # Call the parameterized version with defaults
    return crawl_single_url_with_params.delay(url, job_id, True, True, True)


@shared_task(bind=True, max_retries=3)
def crawl_single_url_with_params(self, url: str, job_id: int = None, classify_topics: bool = True, extract_content: bool = True, respect_robots_txt: bool = True):
    """
    Crawl a single URL and store results with configurable parameters.

    Args:
        url: URL to crawl
        job_id: Optional crawl job ID for tracking
        classify_topics: Whether to classify topics (default: True)
        extract_content: Whether to extract content (default: True)
        respect_robots_txt: Whether to respect robots.txt (default: True)
    """
    # New Relic custom attributes
    if newrelic:
        newrelic.agent.add_custom_attribute('url', url)
        newrelic.agent.add_custom_attribute('job_id', job_id)
        newrelic.agent.add_custom_attribute('classify_topics', classify_topics)
        newrelic.agent.add_custom_attribute('extract_content', extract_content)
        newrelic.agent.add_custom_attribute('respect_robots_txt', respect_robots_txt)

    try:
        # Get or create website
        domain = urlparse(url).netloc
        website, created = Website.objects.get_or_create(domain=domain)
        
        # Check if page already exists
        page, created = CrawledPage.objects.get_or_create(
            url=url,
            defaults={'website': website, 'crawl_status': 'pending'}
        )
        
        if not created and page.crawl_status == 'completed':
            logger.info(f"Page already crawled: {url}")
            return page.id
        
        # Update status to crawling
        page.crawl_status = 'crawling'
        page.save(update_fields=['crawl_status'])
        
        # Crawl the URL with specified parameters
        crawler = WebCrawler(respect_robots_txt=respect_robots_txt)
        result = crawler.crawl_url(url)
        
        # Update page with results
        page.crawl_status = result['status']
        page.title = result['title']
        page.description = result['description']
        page.content = result['content'] if extract_content else None
        page.text_content = result['text_content'] if extract_content else None
        page.status_code = result['status_code']
        page.content_type = result['content_type']
        page.content_length = result['content_length']
        page.encoding = result['encoding']
        page.headers = result['headers']
        page.error_message = result['error_message']
        page.topics = result['topics'] if classify_topics else []

        if result['status'] == 'completed':
            page.crawled_at = timezone.now()
        
        page.save()
        
        # Create PageTopic relationships if topics were classified
        if classify_topics and result['topics'] and len(result['topics']) > 0:
            created_count = 0
            for topic_name in result['topics']:
                # Create topic with proper slug
                from django.utils.text import slugify
                topic_slug = slugify(topic_name)

                topic, created = Topic.objects.get_or_create(
                    name=topic_name,
                    defaults={'slug': topic_slug}
                )

                # Create or update PageTopic relationship
                page_topic, created = PageTopic.objects.get_or_create(
                    page=page,
                    topic=topic,
                    defaults={'confidence': 1.0, 'source': 'automatic'}
                )

                if created:
                    created_count += 1

            logger.info(f"Created {created_count} PageTopic relationships for page {page.id}")

        # Update job progress if job_id provided
        if job_id:
            # Don't pass specific counts, let the task calculate from database
            update_job_progress.delay(job_id)
        
        logger.info(f"Successfully crawled: {url}")
        return page.id
        
    except Exception as exc:
        logger.error(f"Error crawling {url}: {str(exc)}")
        
        # Update page status to failed
        try:
            page = CrawledPage.objects.get(url=url)
            page.crawl_status = 'failed'
            page.error_message = str(exc)
            page.retry_count += 1
            page.save(update_fields=['crawl_status', 'error_message', 'retry_count'])
        except CrawledPage.DoesNotExist:
            pass
        
        # Retry task
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def crawl_bulk_urls(urls: list, job_id: int = None, classify_topics: bool = True, extract_content: bool = True, respect_robots_txt: bool = True):
    """
    Crawl multiple URLs in bulk.
    
    Args:
        urls: List of URLs to crawl
        job_id: Optional crawl job ID for tracking
        classify_topics: Whether to classify topics (default: True)
        extract_content: Whether to extract content (default: True)
        respect_robots_txt: Whether to respect robots.txt (default: True)
    """
    try:
        if job_id:
            job = CrawlJob.objects.get(id=job_id)
            job.job_status = 'running'
            job.started_at = timezone.now()
            job.save(update_fields=['job_status', 'started_at'])
        
        completed_count = 0
        failed_count = 0
        
        for i, url in enumerate(urls):
            try:
                # Crawl single URL with classification parameters
                crawl_single_url_with_params.delay(url, job_id, classify_topics, extract_content, respect_robots_txt)
                completed_count += 1
                
                # Update job progress
                if job_id:
                    update_job_progress.delay(job_id, completed_count, failed_count)
                
                logger.info(f"Queued URL {i+1}/{len(urls)}: {url}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to queue URL {url}: {str(e)}")
        
        # Mark job as completed
        if job_id:
            job = CrawlJob.objects.get(id=job_id)
            job.job_status = 'completed'
            job.completed_at = timezone.now()
            job.completed_urls = completed_count
            job.failed_urls = failed_count
            job.progress = 100.0
            job.save(update_fields=['job_status', 'completed_at', 'completed_urls', 'failed_urls', 'progress'])
        
        logger.info(f"Bulk crawl completed: {completed_count} successful, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error in bulk crawl: {str(e)}")
        
        # Mark job as failed
        if job_id:
            try:
                job = CrawlJob.objects.get(id=job_id)
                job.job_status = 'failed'
                job.completed_at = timezone.now()
                job.save(update_fields=['job_status', 'completed_at'])
            except CrawlJob.DoesNotExist:
                pass


@shared_task
def update_job_progress(job_id: int, completed_count: int = None, failed_count: int = None):
    """
    Update crawl job progress.
    
    Args:
        job_id: Crawl job ID
        completed_count: Number of completed URLs (optional)
        failed_count: Number of failed URLs (optional)
    """
    try:
        job = CrawlJob.objects.get(id=job_id)
        
        # If counts are provided, use them; otherwise calculate from database
        if completed_count is None or failed_count is None:
            # Get all URLs for this job
            job_urls = job.urls_list if hasattr(job, 'urls_list') else []
            
            # Count completed and failed URLs
            completed_count = CrawledPage.objects.filter(
                url__in=job_urls,
                crawl_status='completed'
            ).count()
            
            failed_count = CrawledPage.objects.filter(
                url__in=job_urls,
                crawl_status='failed'
            ).count()
        
        # Update job
        job.completed_urls = completed_count
        job.failed_urls = failed_count
        
        if job.total_urls > 0:
            job.progress = ((completed_count + failed_count) / job.total_urls) * 100
        else:
            job.progress = 0.0
        
        job.save(update_fields=['completed_urls', 'failed_urls', 'progress'])
        
        logger.info(f"Updated job {job_id} progress: {job.progress:.1f}% ({completed_count} completed, {failed_count} failed)")
        
    except CrawlJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
    except Exception as e:
        logger.error(f"Error updating job progress: {str(e)}")


@shared_task
def classify_page_topics(page_id: int):
    """
    Classify topics for a specific page.
    
    Args:
        page_id: Page ID to classify
    """
    try:
        page = CrawledPage.objects.get(id=page_id)
        
        # Use existing topics from the page if available, otherwise classify
        if page.topics and isinstance(page.topics, list) and len(page.topics) > 0:
            topics = page.topics
            logger.info(f"Using existing topics for page {page_id}: {topics}")
        else:
            if not page.text_content:
                logger.warning(f"No text content available for page {page_id}")
                return
            
            # Use the crawler's topic classification
            crawler = WebCrawler()
            topics = crawler._classify_topics(
                page.title, 
                page.description, 
                page.text_content
            )
            
            # Update page topics
            page.topics = topics
            page.save(update_fields=['topics'])
            logger.info(f"Classified new topics for page {page_id}: {topics}")
        
        # Create PageTopic relationships for all topics
        created_count = 0
        for topic_name in topics:
            # Create topic with proper slug
            from django.utils.text import slugify
            topic_slug = slugify(topic_name)
            
            topic, created = Topic.objects.get_or_create(
                name=topic_name,
                defaults={'slug': topic_slug}
            )
            
            # Create or update PageTopic relationship
            page_topic, created = PageTopic.objects.get_or_create(
                page=page,
                topic=topic,
                defaults={'confidence': 1.0, 'source': 'automatic'}
            )
            
            if created:
                created_count += 1
        
        logger.info(f"Created {created_count} PageTopic relationships for page {page_id}")
        
    except CrawledPage.DoesNotExist:
        logger.error(f"Page {page_id} not found")
    except Exception as e:
        logger.error(f"Error classifying topics for page {page_id}: {str(e)}")


@shared_task
def cleanup_old_data(days: int = 30):
    """
    Clean up old crawled data.
    
    Args:
        days: Number of days to keep data
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Soft delete old pages
        old_pages = CrawledPage.objects.filter(
            created_at__lt=cutoff_date,
            is_active=True
        )
        deleted_count = old_pages.count()
        
        for page in old_pages:
            page.delete()  # This will soft delete
        
        logger.info(f"Cleaned up {deleted_count} old pages")
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")


@shared_task
def retry_failed_urls(max_retries: int = 3):
    """
    Retry failed URLs that haven't exceeded max retries.
    
    Args:
        max_retries: Maximum number of retries
    """
    try:
        failed_pages = CrawledPage.objects.filter(
            crawl_status='failed',
            retry_count__lt=max_retries,
            is_active=True
        )
        
        retry_count = 0
        for page in failed_pages:
            try:
                # Reset retry count and status
                page.crawl_status = 'pending'
                page.error_message = ''
                page.save(update_fields=['crawl_status', 'error_message'])
                
                # Queue for crawling
                crawl_single_url.delay(page.url)
                retry_count += 1
                
            except Exception as e:
                logger.error(f"Error retrying page {page.url}: {str(e)}")
        
        logger.info(f"Queued {retry_count} failed URLs for retry")
        
    except Exception as e:
        logger.error(f"Error retrying failed URLs: {str(e)}")


@shared_task
def update_website_stats():
    """
    Update website statistics.
    """
    try:
        websites = Website.active_objects.all()
        
        for website in websites:
            # Count total pages
            total_pages = website.pages.filter(is_active=True).count()
            
            # Count completed pages
            completed_pages = website.pages.filter(
                is_active=True,
                crawl_status='completed'
            ).count()
            
            # Update website stats
            website.total_pages = total_pages
            website.last_crawled = website.pages.filter(
                is_active=True,
                crawl_status='completed'
            ).order_by('-crawled_at').values_list('crawled_at', flat=True).first()
            
            website.save(update_fields=['total_pages', 'last_crawled'])
        
        logger.info(f"Updated stats for {websites.count()} websites")
        
    except Exception as e:
        logger.error(f"Error updating website stats: {str(e)}")


@shared_task
def sync_topic_counts():
    """
    Synchronize topic page counts.
    """
    try:
        topics = Topic.active_objects.all()
        
        for topic in topics:
            # Count active pages with this topic
            page_count = PageTopic.objects.filter(
                topic=topic,
                page__is_active=True
            ).count()
            
            topic.page_count = page_count
            topic.save(update_fields=['page_count'])
        
        logger.info(f"Updated page counts for {topics.count()} topics")
        
    except Exception as e:
        logger.error(f"Error syncing topic counts: {str(e)}")
