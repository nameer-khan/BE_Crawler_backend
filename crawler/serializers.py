"""
Django REST Framework serializers for the crawler app.
"""

from rest_framework import serializers
from .models import Website, CrawledPage, CrawlJob, Topic, PageTopic


class WebsiteSerializer(serializers.ModelSerializer):
    """Serializer for Website model."""
    
    class Meta:
        model = Website
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TopicSerializer(serializers.ModelSerializer):
    """Serializer for Topic model."""
    
    class Meta:
        model = Topic
        fields = '__all__'
        read_only_fields = ('created_at',)


class PageTopicSerializer(serializers.ModelSerializer):
    """Serializer for PageTopic model."""
    topic = TopicSerializer(read_only=True)
    
    class Meta:
        model = PageTopic
        fields = '__all__'
        read_only_fields = ('created_at',)


class CrawledPageSerializer(serializers.ModelSerializer):
    """Serializer for CrawledPage model."""
    website = WebsiteSerializer(read_only=True)
    page_topics = PageTopicSerializer(many=True, read_only=True)
    
    class Meta:
        model = CrawledPage
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'crawled_at')


class CrawledPageListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing crawled pages."""
    website_domain = serializers.CharField(source='website.domain', read_only=True)
    
    class Meta:
        model = CrawledPage
        fields = [
            'id', 'url', 'website_domain', 'title', 'status', 
            'status_code', 'topics', 'created_at', 'crawled_at'
        ]
        read_only_fields = ('created_at', 'crawled_at')


class CrawlJobSerializer(serializers.ModelSerializer):
    """Serializer for CrawlJob model."""
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = CrawlJob
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')
    
    def get_progress_percentage(self, obj):
        """Calculate progress percentage."""
        return obj.get_progress_percentage()


class CrawlJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating crawl jobs."""
    
    class Meta:
        model = CrawlJob
        fields = ['name', 'description', 'urls_file', 'urls_list', 'batch_size', 'max_workers']


class URLProcessRequestSerializer(serializers.Serializer):
    """Serializer for single URL processing requests."""
    url = serializers.URLField()
    extract_content = serializers.BooleanField(default=True)
    classify_topics = serializers.BooleanField(default=True)
    respect_robots_txt = serializers.BooleanField(default=True)


class URLProcessResponseSerializer(serializers.Serializer):
    """Serializer for URL processing responses."""
    url = serializers.URLField()
    status = serializers.CharField()
    title = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    content_preview = serializers.CharField(allow_null=True)
    topics = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    status_code = serializers.IntegerField(allow_null=True)
    content_type = serializers.CharField(allow_null=True)
    content_length = serializers.IntegerField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)
    processing_time = serializers.FloatField()
    crawled_at = serializers.DateTimeField()


class BulkURLProcessRequestSerializer(serializers.Serializer):
    """Serializer for bulk URL processing requests."""
    urls = serializers.ListField(
        child=serializers.URLField(),
        min_length=1,
        max_length=1000
    )
    extract_content = serializers.BooleanField(default=True)
    classify_topics = serializers.BooleanField(default=True)
    respect_robots_txt = serializers.BooleanField(default=True)
    batch_size = serializers.IntegerField(default=10, min_value=1, max_value=100)


class CrawlJobStatusSerializer(serializers.Serializer):
    """Serializer for crawl job status responses."""
    job_id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    progress_percentage = serializers.FloatField()
    total_urls = serializers.IntegerField()
    processed_urls = serializers.IntegerField()
    successful_urls = serializers.IntegerField()
    failed_urls = serializers.IntegerField()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    estimated_completion = serializers.DateTimeField(allow_null=True)
