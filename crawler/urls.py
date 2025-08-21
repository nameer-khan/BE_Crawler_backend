"""
URL configuration for the crawler app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # API root
    path('', views.api_root, name='api-root'),
    
    # Website endpoints
    path('websites/', views.WebsiteAPIView.as_view(), name='websites'),
    
    # CrawledPage endpoints
    path('pages/', views.CrawledPageAPIView.as_view(), name='pages'),
    path('pages/<int:page_id>/', views.CrawledPageDetailAPIView.as_view(), name='page-detail'),
    path('pages/<int:page_id>/topics/', views.CrawledPageTopicsAPIView.as_view(), name='page-topics'),
    
    # CrawlJob endpoints
    path('jobs/', views.CrawlJobAPIView.as_view(), name='jobs'),
    path('jobs/<int:job_id>/', views.CrawlJobDetailAPIView.as_view(), name='job-detail'),
    path('jobs/<int:job_id>/cancel/', views.CrawlJobCancelAPIView.as_view(), name='job-cancel'),
    path('jobs/<int:job_id>/status/', views.CrawlJobStatusAPIView.as_view(), name='job-status'),
    
    # Topic endpoints
    path('topics/', views.TopicAPIView.as_view(), name='topics'),
    
    # Crawler operation endpoints
    path('crawler/url/', views.CrawlURLAPIView.as_view(), name='crawl-url'),
    path('crawler/bulk/', views.CrawlBulkAPIView.as_view(), name='crawl-bulk'),
    path('crawler/file/', views.CrawlFromFileAPIView.as_view(), name='crawl-from-file'),
    path('crawler/stats/', views.CrawlerStatsAPIView.as_view(), name='crawler-stats'),
]
