"""
Custom Prometheus metrics for Junkbin.io business analytics.
"""
from prometheus_client import Counter, Histogram

# Search metrics
search_counter = Counter(
    'junkbin_searches_total',
    'Total search queries',
    ['has_results'],
)

# Component view metrics
component_view_counter = Counter(
    'junkbin_component_views_total',
    'Component detail page views',
)

# Content submission metrics
submission_counter = Counter(
    'junkbin_submissions_total',
    'Content submissions',
    ['content_type'],
)

# Search latency
search_latency = Histogram(
    'junkbin_search_duration_seconds',
    'Search request duration in seconds',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)
