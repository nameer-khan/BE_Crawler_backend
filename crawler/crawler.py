"""
Core crawler engine for extracting content and classifying topics.
"""

import time
import logging
from urllib.parse import urlparse
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from readability import Document
from textblob import TextBlob
from django.conf import settings

logger = logging.getLogger(__name__)

class WebCrawler:
    def __init__(self, user_agent: Optional[str] = None, request_timeout: Optional[int] = None,
                 max_retries: Optional[int] = None, delay_between_requests: Optional[int] = None,
                 respect_robots_txt: bool = True):
        self.user_agent = user_agent or settings.CRAWLER_SETTINGS['USER_AGENT']
        self.request_timeout = request_timeout or settings.CRAWLER_SETTINGS['REQUEST_TIMEOUT']
        self.max_retries = max_retries or settings.CRAWLER_SETTINGS['MAX_RETRIES']
        self.delay_between_requests = delay_between_requests or settings.CRAWLER_SETTINGS['DELAY_BETWEEN_REQUESTS']
        self.respect_robots_txt = respect_robots_txt or settings.CRAWLER_SETTINGS['RESPECT_ROBOTS_TXT']
        self.max_content_length = settings.CRAWLER_SETTINGS['MAX_CONTENT_LENGTH']

        # Predefined topic keywords for classification
        self.topic_keywords = {
            'technology': ['technology', 'software', 'hardware', 'computer', 'digital', 'ai', 'machine learning', 'programming', 'code'],
            'business': ['business', 'finance', 'economy', 'market', 'investment', 'startup', 'company', 'corporate'],
            'health': ['health', 'medical', 'medicine', 'healthcare', 'wellness', 'fitness', 'doctor', 'hospital'],
            'sports': ['sports', 'athletics', 'football', 'basketball', 'baseball', 'soccer', 'game', 'team'],
            'politics': ['politics', 'government', 'election', 'policy', 'democracy', 'president', 'congress'],
            'entertainment': ['entertainment', 'movie', 'music', 'celebrity', 'film', 'television', 'show'],
            'science': ['science', 'research', 'study', 'experiment', 'discovery', 'scientific', 'laboratory'],
            'education': ['education', 'learning', 'school', 'university', 'teaching', 'student', 'course'],
            'travel': ['travel', 'tourism', 'vacation', 'destination', 'hotel', 'trip', 'journey'],
            'food': ['food', 'cooking', 'recipe', 'restaurant', 'cuisine', 'kitchen', 'chef'],
            'automotive': ['car', 'automotive', 'vehicle', 'automobile', 'driving', 'motor', 'engine'],
            'fashion': ['fashion', 'style', 'clothing', 'design', 'trend', 'wear', 'outfit'],
            'real_estate': ['real estate', 'property', 'housing', 'home', 'mortgage', 'house', 'apartment'],
            'environment': ['environment', 'climate', 'sustainability', 'green', 'ecology', 'nature', 'earth']
        }

    def crawl_url(self, url: str) -> Dict:
        """
        Crawl a URL and extract content and metadata.
        
        Args:
            url: URL to crawl
            
        Returns:
            Dictionary containing crawled data
        """
        try:
            # Check robots.txt if enabled
            if self.respect_robots_txt:
                if not self._check_robots_txt(url):
                    return {
                        'status': 'blocked',
                        'error_message': 'Blocked by robots.txt',
                        'url': url,
                        'title': None,
                        'description': None,
                        'keywords': None,
                        'author': None,
                        'language': None,
                        'content': None,
                        'text_content': None,
                        'topics': [],
                        'status_code': None,
                        'content_type': None,
                        'content_length': None,
                        'encoding': None,
                        'headers': {},
                    }

            # Fetch the URL
            response = self._fetch_url(url)
            if not response:
                return {
                    'status': 'failed',
                    'error_message': 'Failed to fetch URL',
                    'url': url,
                    'title': None,
                    'description': None,
                    'keywords': None,
                    'author': None,
                    'language': None,
                    'content': None,
                    'text_content': None,
                    'topics': [],
                    'status_code': None,
                    'content_type': None,
                    'content_length': None,
                    'encoding': None,
                    'headers': {},
                }

            # Check if response is HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                return {
                    'status': 'failed',
                    'error_message': f'Not an HTML page. Content-Type: {content_type}',
                    'url': url,
                    'title': None,
                    'description': None,
                    'keywords': None,
                    'author': None,
                    'language': None,
                    'content': None,
                    'text_content': None,
                    'topics': [],
                    'status_code': response.status_code,
                    'content_type': content_type,
                    'content_length': len(response.content),
                    'encoding': response.encoding,
                    'headers': dict(response.headers),
                }

            # Parse the content
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
            except Exception as parse_error:
                logger.error(f"Error parsing HTML for {url}: {str(parse_error)}")
                return {
                    'status': 'failed',
                    'error_message': f'Error parsing HTML: {str(parse_error)}',
                    'url': url,
                    'title': None,
                    'description': None,
                    'keywords': None,
                    'author': None,
                    'language': None,
                    'content': None,
                    'text_content': None,
                    'topics': [],
                    'status_code': response.status_code,
                    'content_type': content_type,
                    'content_length': len(response.content),
                    'encoding': response.encoding,
                    'headers': dict(response.headers),
                }
            
            # Extract metadata with error handling
            try:
                title = self._extract_title(soup)
            except Exception as e:
                logger.warning(f"Error extracting title for {url}: {str(e)}")
                title = None
                
            try:
                description = self._extract_description(soup)
            except Exception as e:
                logger.warning(f"Error extracting description for {url}: {str(e)}")
                description = None
                
            try:
                keywords = self._extract_keywords(soup)
            except Exception as e:
                logger.warning(f"Error extracting keywords for {url}: {str(e)}")
                keywords = None
                
            try:
                author = self._extract_author(soup)
            except Exception as e:
                logger.warning(f"Error extracting author for {url}: {str(e)}")
                author = None
                
            try:
                language = self._extract_language(soup)
            except Exception as e:
                logger.warning(f"Error extracting language for {url}: {str(e)}")
                language = 'en'
            
            # Extract main content using readability
            try:
                content = self._extract_content(response.content)
            except Exception as e:
                logger.warning(f"Error extracting content for {url}: {str(e)}")
                content = None
                
            try:
                text_content = self._extract_text_content(soup)
            except Exception as e:
                logger.warning(f"Error extracting text content for {url}: {str(e)}")
                text_content = None
            
            # Classify topics
            try:
                topics = self._classify_topics(title, description, text_content)
            except Exception as e:
                logger.warning(f"Error classifying topics for {url}: {str(e)}")
                topics = []
            
            return {
                'status': 'completed',
                'url': url,
                'title': title,
                'description': description,
                'keywords': keywords,
                'author': author,
                'language': language,
                'content': content,
                'text_content': text_content,
                'topics': topics,
                'status_code': response.status_code,
                'content_type': content_type,
                'content_length': len(response.content),
                'encoding': response.encoding,
                'headers': dict(response.headers),
                'error_message': None
            }
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return {
                'status': 'failed',
                'url': url,
                'error_message': str(e),
                'title': None,
                'description': None,
                'keywords': None,
                'author': None,
                'language': None,
                'content': None,
                'text_content': None,
                'topics': [],
                'status_code': None,
                'content_type': None,
                'content_length': None,
                'encoding': None,
                'headers': {},
            }

    def _fetch_url(self, url: str) -> Optional[requests.Response]:
        """Fetch URL with retry logic."""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.request_timeout,
                    allow_redirects=True
                )
                
                # Check if content is too large
                if len(response.content) > self.max_content_length:
                    logger.warning(f"Content too large for {url}: {len(response.content)} bytes")
                    return None
                
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All attempts failed for {url}")
                    return None
        
        return None

    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                return self._parse_robots_txt(response.text, parsed_url.path)
            
            return True  # Allow if robots.txt doesn't exist
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {str(e)}")
            return True  # Allow if we can't check

    def _parse_robots_txt(self, robots_content: str, url_path: str) -> bool:
        """Parse robots.txt content and check if URL is allowed."""
        try:
            lines = robots_content.split('\n')
            current_user_agent = None
            disallow_rules = []
            allow_rules = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'user-agent':
                        # If we find a new user-agent, reset rules
                        if value == '*' or value.lower() in self.user_agent.lower():
                            current_user_agent = value
                            disallow_rules = []
                            allow_rules = []
                        else:
                            current_user_agent = None
                            disallow_rules = []
                            allow_rules = []
                    
                    elif key == 'disallow' and current_user_agent:
                        disallow_rules.append(value)
                    
                    elif key == 'allow' and current_user_agent:
                        allow_rules.append(value)
            
            # Check if URL is disallowed
            for rule in disallow_rules:
                if self._path_matches_rule(url_path, rule):
                    # Check if there's a more specific allow rule
                    for allow_rule in allow_rules:
                        if self._path_matches_rule(url_path, allow_rule):
                            return True
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error parsing robots.txt: {str(e)}")
            return True

    def _path_matches_rule(self, path: str, rule: str) -> bool:
        """Check if a path matches a robots.txt rule."""
        if not rule:
            return False
        
        # Handle wildcards
        if '*' in rule:
            # Simple wildcard matching
            rule_pattern = rule.replace('*', '.*')
            import re
            return bool(re.match(rule_pattern, path))
        
        # Exact match or prefix match
        return path.startswith(rule)

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Fallback to h1
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page description."""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        
        # Try Open Graph description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            return og_desc.get('content', '').strip()
        
        return None

    def _extract_keywords(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page keywords."""
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            return meta_keywords.get('content', '').strip()
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page author."""
        # Try various author meta tags
        author_selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            'meta[name="twitter:creator"]'
        ]
        
        for selector in author_selectors:
            author_tag = soup.select_one(selector)
            if author_tag:
                return author_tag.get('content', '').strip()
        
        return None

    def _extract_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page language."""
        # Try html lang attribute
        html_tag = soup.find('html')
        if html_tag:
            lang = html_tag.get('lang')
            if lang:
                return lang
        
        # Try meta http-equiv
        meta_lang = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if meta_lang:
            return meta_lang.get('content', '').strip()
        
        return 'en'  # Default to English

    def _extract_content(self, html_content: bytes) -> Optional[str]:
        """Extract main content using readability."""
        try:
            doc = Document(html_content)
            return doc.summary()
        except Exception as e:
            logger.warning(f"Error extracting content: {str(e)}")
            return None

    def _extract_text_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract clean text content."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text if text else None

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for topic classification."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Basic cleaning
        import re
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _classify_topics(self, title: Optional[str], description: Optional[str], text_content: Optional[str]) -> List[str]:
        """Classify topics based on content."""
        if not any([title, description, text_content]):
            return []
        
        # Combine all text
        combined_text = ' '.join(filter(None, [title or '', description or '', text_content or '']))
        processed_text = self._preprocess_text(combined_text)
        
        if not processed_text:
            return []
        
        # Simple keyword-based classification
        found_topics = []
        text_words = set(processed_text.split())
        
        for topic, keywords in self.topic_keywords.items():
            topic_keywords_set = set(keywords)
            if text_words.intersection(topic_keywords_set):
                found_topics.append(topic)
        
        # Limit to top 3 topics
        return found_topics[:3]
