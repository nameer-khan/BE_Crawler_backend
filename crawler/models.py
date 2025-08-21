"""
Django models for the crawler app.
"""

from django.db import models
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import json

from .mixins import (
    BaseModel, BaseModelWithName, BaseModelWithSlug,
    TimestampMixin, SoftDeleteMixin,
    ActiveManager, DeletedManager
)


class Website(BaseModelWithName):
    """
    Model to store website information.
    """
    domain = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("Domain"),
        help_text=_("Website domain (e.g., example.com)")
    )
    
    # Override name field to be optional since we have domain
    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Name"),
        help_text=_("Website name (optional, defaults to domain)")
    )
    
    robots_txt_url = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("Robots.txt URL"),
        help_text=_("URL to the robots.txt file")
    )
    
    crawl_delay = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Crawl Delay"),
        help_text=_("Delay between requests in seconds")
    )
    
    last_crawled = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Last Crawled"),
        help_text=_("When this website was last crawled")
    )
    
    total_pages = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Pages"),
        help_text=_("Total number of pages crawled from this website")
    )

    # Custom managers
    objects = models.Manager()
    active_objects = ActiveManager()
    deleted_objects = DeletedManager()

    class Meta:
        db_table = 'websites'
        verbose_name = _("Website")
        verbose_name_plural = _("Websites")
        ordering = ['-created_at']

    def __str__(self):
        return self.name or self.domain

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.domain
        super().save(*args, **kwargs)

    @property
    def robots_txt_content(self):
        """Get robots.txt content if available."""
        if self.robots_txt_url:
            try:
                import requests
                response = requests.get(self.robots_txt_url, timeout=10)
                if response.status_code == 200:
                    return response.text
            except:
                pass
        return None


class CrawledPage(BaseModel):
    """
    Model to store crawled page information.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('crawling', _('Crawling')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('blocked', _('Blocked')),
    ]

    url = models.URLField(
        max_length=2048,
        unique=True,
        verbose_name=_("URL"),
        help_text=_("The URL that was crawled")
    )
    website = models.ForeignKey(
        Website,
        on_delete=models.CASCADE,
        related_name='pages',
        verbose_name=_("Website"),
        help_text=_("Website this page belongs to")
    )
    
    # Metadata
    title = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Title"),
        help_text=_("Page title")
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Page description/meta description")
    )
    keywords = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Keywords"),
        help_text=_("Page keywords/meta keywords")
    )
    author = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Author"),
        help_text=_("Page author")
    )
    language = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_("Language"),
        help_text=_("Page language code")
    )
    
    # Content
    content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Content"),
        help_text=_("Full HTML content")
    )
    text_content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Text Content"),
        help_text=_("Extracted text content")
    )
    
    # Technical info
    status_code = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Status Code"),
        help_text=_("HTTP status code")
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Content Type"),
        help_text=_("HTTP content type")
    )
    content_length = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Content Length"),
        help_text=_("Content length in bytes")
    )
    encoding = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Encoding"),
        help_text=_("Content encoding")
    )
    
    # Headers
    headers = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Headers"),
        help_text=_("HTTP response headers")
    )
    
    # Crawling status (override BaseModel status)
    crawl_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Crawl Status"),
        help_text=_("Current crawling status")
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Error Message"),
        help_text=_("Error message if crawling failed")
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Retry Count"),
        help_text=_("Number of retry attempts")
    )
    
    # Timestamps (override BaseModel timestamps for crawling-specific ones)
    crawled_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Crawled At"),
        help_text=_("When this page was last crawled")
    )
    
    # Classification
    topics = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Topics"),
        help_text=_("Identified topics for this page")
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Category"),
        help_text=_("Page category")
    )
    sentiment = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("Sentiment"),
        help_text=_("Content sentiment analysis")
    )

    # Custom managers
    objects = models.Manager()
    active_objects = ActiveManager()
    deleted_objects = DeletedManager()

    class Meta:
        db_table = 'crawled_pages'
        verbose_name = _("Crawled Page")
        verbose_name_plural = _("Crawled Pages")
        indexes = [
            models.Index(fields=['crawl_status']),
            models.Index(fields=['website']),
            models.Index(fields=['created_at']),
            models.Index(fields=['crawled_at']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.url} ({self.crawl_status})"

    def set_topics(self, topics_list):
        """Set topics for this page."""
        self.topics = topics_list
        self.save(update_fields=['topics'])

    def get_topics(self):
        """Get topics for this page."""
        return self.topics if isinstance(self.topics, list) else []

    def mark_as_crawled(self):
        """Mark this page as successfully crawled."""
        self.crawl_status = 'completed'
        self.crawled_at = timezone.now()
        self.save(update_fields=['crawl_status', 'crawled_at'])

    def mark_as_failed(self, error_message):
        """Mark this page as failed to crawl."""
        self.crawl_status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['crawl_status', 'error_message', 'retry_count'])

    @property
    def is_crawlable(self):
        """Check if this page can be crawled."""
        return self.crawl_status in ['pending', 'failed'] and self.retry_count < 3


class CrawlJob(BaseModelWithName):
    """
    Model to store crawl job information.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]

    total_urls = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total URLs"),
        help_text=_("Total number of URLs to crawl")
    )
    completed_urls = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Completed URLs"),
        help_text=_("Number of successfully crawled URLs")
    )
    failed_urls = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Failed URLs"),
        help_text=_("Number of failed URLs")
    )
    progress = models.FloatField(
        default=0.0,
        verbose_name=_("Progress"),
        help_text=_("Job progress percentage")
    )
    batch_size = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Batch Size"),
        help_text=_("Number of URLs to process in each batch")
    )
    
    # URLs can be stored as list or file
    urls_list = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("URLs List"),
        help_text=_("List of URLs to crawl")
    )
    urls_file = models.FileField(
        upload_to='crawl_jobs/',
        blank=True,
        null=True,
        verbose_name=_("URLs File"),
        help_text=_("File containing URLs to crawl")
    )
    
    # Job timing
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Started At"),
        help_text=_("When the job started")
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Completed At"),
        help_text=_("When the job completed")
    )
    
    # Override status field for job-specific status
    job_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Job Status"),
        help_text=_("Current job status")
    )

    # Custom managers
    objects = models.Manager()
    active_objects = ActiveManager()
    deleted_objects = DeletedManager()

    class Meta:
        db_table = 'crawl_jobs'
        verbose_name = _("Crawl Job")
        verbose_name_plural = _("Crawl Jobs")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.job_status})"

    def get_progress_percentage(self):
        """Calculate job progress percentage."""
        if self.total_urls == 0:
            return 0.0
        return (self.completed_urls + self.failed_urls) / self.total_urls * 100

    def start_job(self):
        """Start the crawl job."""
        self.job_status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['job_status', 'started_at'])

    def complete_job(self):
        """Mark job as completed."""
        self.job_status = 'completed'
        self.completed_at = timezone.now()
        self.progress = 100.0
        self.save(update_fields=['job_status', 'completed_at', 'progress'])

    def fail_job(self):
        """Mark job as failed."""
        self.job_status = 'failed'
        self.completed_at = timezone.now()
        self.save(update_fields=['job_status', 'completed_at'])

    def cancel_job(self):
        """Cancel the job."""
        self.job_status = 'cancelled'
        self.completed_at = timezone.now()
        self.save(update_fields=['job_status', 'completed_at'])

    @property
    def processed_urls(self):
        """Get total processed URLs."""
        return self.completed_urls + self.failed_urls

    @property
    def successful_urls(self):
        """Get successfully processed URLs."""
        return self.completed_urls


class Topic(BaseModelWithName):
    """
    Model to store topic information.
    """
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("URL-friendly topic identifier")
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='children',
        verbose_name=_("Parent Topic"),
        help_text=_("Parent topic if this is a subtopic")
    )
    
    keywords = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Keywords"),
        help_text=_("Keywords associated with this topic")
    )
    
    page_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Page Count"),
        help_text=_("Number of pages tagged with this topic")
    )

    # Custom managers
    objects = models.Manager()
    active_objects = ActiveManager()
    deleted_objects = DeletedManager()

    class Meta:
        db_table = 'topics'
        verbose_name = _("Topic")
        verbose_name_plural = _("Topics")
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_all_children(self):
        """Get all child topics recursively."""
        children = []
        for child in self.children.all():
            children.append(child)
            children.extend(child.get_all_children())
        return children

    def get_all_parents(self):
        """Get all parent topics recursively."""
        parents = []
        if self.parent:
            parents.append(self.parent)
            parents.extend(self.parent.get_all_parents())
        return parents


class PageTopic(BaseModel):
    """
    Model to store the relationship between pages and topics.
    """
    page = models.ForeignKey(
        CrawledPage,
        on_delete=models.CASCADE,
        related_name='page_topics',
        verbose_name=_("Page"),
        help_text=_("Crawled page")
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='page_topics',
        verbose_name=_("Topic"),
        help_text=_("Topic")
    )
    confidence = models.FloatField(
        default=1.0,
        verbose_name=_("Confidence"),
        help_text=_("Confidence score for this topic assignment")
    )
    source = models.CharField(
        max_length=50,
        default='automatic',
        verbose_name=_("Source"),
        help_text=_("Source of topic assignment (automatic/manual)")
    )

    # Custom managers
    objects = models.Manager()
    active_objects = ActiveManager()
    deleted_objects = DeletedManager()

    class Meta:
        db_table = 'page_topics'
        verbose_name = _("Page Topic")
        verbose_name_plural = _("Page Topics")
        unique_together = ['page', 'topic']
        ordering = ['-confidence']

    def __str__(self):
        return f"{self.page.url} - {self.topic.name} ({self.confidence})"
