"""
Django admin configuration for the crawler app.
"""

from django.contrib import admin
from .models import Website, CrawledPage, CrawlJob, Topic, PageTopic


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ['domain', 'name', 'crawl_delay', 'total_pages', 'last_crawled', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at', 'is_active']
    search_fields = ['domain', 'name']
    readonly_fields = ['created_at', 'updated_at', 'total_pages', 'last_crawled']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('domain', 'name', 'description', 'is_active')
        }),
        ('Crawling Configuration', {
            'fields': ('robots_txt_url', 'crawl_delay')
        }),
        ('Statistics', {
            'fields': ('total_pages', 'last_crawled'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CrawledPage)
class CrawledPageAdmin(admin.ModelAdmin):
    list_display = ['url', 'website', 'title', 'crawl_status', 'status_code', 'created_at', 'crawled_at']
    list_filter = ['crawl_status', 'status_code', 'website', 'created_at', 'crawled_at', 'is_active']
    search_fields = ['url', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at', 'crawled_at']
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('url', 'website', 'crawl_status', 'error_message', 'retry_count', 'is_active')
        }),
        ('Content', {
            'fields': ('title', 'description', 'keywords', 'author', 'language')
        }),
        ('Technical', {
            'fields': ('status_code', 'content_type', 'content_length', 'encoding', 'headers')
        }),
        ('Classification', {
            'fields': ('topics', 'category', 'sentiment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'crawled_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CrawlJob)
class CrawlJobAdmin(admin.ModelAdmin):
    list_display = ['name', 'job_status', 'total_urls', 'completed_urls', 'failed_urls', 'progress', 'created_at']
    list_filter = ['job_status', 'created_at', 'started_at', 'completed_at', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at', 'progress']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'job_status', 'is_active')
        }),
        ('Configuration', {
            'fields': ('urls_file', 'urls_list', 'batch_size')
        }),
        ('Progress', {
            'fields': ('total_urls', 'completed_urls', 'failed_urls', 'progress')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'page_count', 'created_at']
    list_filter = ['parent', 'created_at', 'is_active']
    search_fields = ['name', 'description', 'slug']
    readonly_fields = ['created_at', 'page_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        ('Hierarchy', {
            'fields': ('parent',)
        }),
        ('Keywords', {
            'fields': ('keywords',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('page_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PageTopic)
class PageTopicAdmin(admin.ModelAdmin):
    list_display = ['page', 'topic', 'confidence', 'source', 'created_at']
    list_filter = ['topic', 'confidence', 'source', 'created_at', 'is_active']
    search_fields = ['page__url', 'page__title', 'topic__name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Relationship', {
            'fields': ('page', 'topic', 'is_active')
        }),
        ('Classification', {
            'fields': ('confidence', 'source')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
