"""
System status dashboard for Django admin.
"""
import json
import logging
from datetime import timedelta

import psutil
from celery import current_app
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

STATUS_CACHE_KEY = '_system_status_result'
STATUS_CACHE_TTL = 30  # seconds


def _check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return {'status': 'ok', 'detail': connection.settings_dict.get('NAME', '')}
    except Exception as e:
        logger.error('Status check database error: %s', e)
        return {'status': 'error', 'detail': str(e)}


def _check_redis():
    try:
        cache.set('_status_check', 'ok', 10)
        if cache.get('_status_check') == 'ok':
            return {'status': 'ok', 'detail': 'Read/write OK'}
        return {'status': 'error', 'detail': 'Read-back mismatch'}
    except Exception as e:
        logger.error('Status check cache error: %s', e)
        return {'status': 'error', 'detail': str(e)}


def _check_celery():
    try:
        inspector = current_app.control.inspect(timeout=3.0)
        ping = inspector.ping()
        if ping:
            workers = list(ping.keys())
            return {
                'status': 'ok',
                'detail': f'{len(workers)} worker(s): {", ".join(workers)}',
            }
        return {'status': 'error', 'detail': 'No workers responded'}
    except Exception as e:
        logger.error('Status check celery error: %s', e)
        return {'status': 'error', 'detail': str(e)}


def _check_celery_beat():
    try:
        from django_celery_beat.models import PeriodicTask
        active = PeriodicTask.objects.filter(enabled=True).count()
        total = PeriodicTask.objects.count()
        return {
            'status': 'ok' if active > 0 else 'warn',
            'detail': f'{active} active / {total} total scheduled tasks',
        }
    except Exception as e:
        logger.error('Status check celery-beat error: %s', e)
        return {'status': 'error', 'detail': str(e)}


def _get_system_metrics():
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/app')
    return {
        'cpu': {'percent': cpu},
        'memory': {
            'used': _fmt_bytes(mem.used),
            'total': _fmt_bytes(mem.total),
            'percent': mem.percent,
        },
        'disk': {
            'used': _fmt_bytes(disk.used),
            'total': _fmt_bytes(disk.total),
            'percent': disk.percent,
        },
    }


def _fmt_bytes(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} PB'


def _get_recent_tasks():
    try:
        from django_celery_results.models import TaskResult
        tasks = TaskResult.objects.order_by('-date_done')[:25]
        since = timezone.now() - timedelta(hours=24)
        failures_24h = TaskResult.objects.filter(
            status='FAILURE', date_done__gte=since
        ).count()
        return {
            'tasks': [
                {
                    'name': t.task_name or t.task_id[:12],
                    'status': t.status,
                    'date_done': t.date_done,
                    'runtime': f'{t.meta.get("runtime", "-")}' if isinstance(t.meta, dict) else '-',
                }
                for t in tasks
            ],
            'failures_24h': failures_24h,
        }
    except Exception as e:
        logger.error('Status check tasks error: %s', e)
        return {'tasks': [], 'failures_24h': 0}


def _get_app_stats():
    from apps.products.models import Product, Schematic
    from apps.components.models import Component
    from apps.reports.models import Report, UserReview
    from django.contrib.auth import get_user_model

    User = get_user_model()

    products_total = Product.objects.count()
    products_approved = Product.objects.filter(is_approved=True).count()
    return {
        'products_total': products_total,
        'products_approved': products_approved,
        'products_pending': products_total - products_approved,
        'components': Component.objects.count(),
        'schematics': Schematic.objects.filter(is_approved=True).count(),
        'users': User.objects.count(),
        'pending_reports': Report.objects.filter(status='pending').count(),
        'pending_reviews': UserReview.objects.filter(status='pending').count(),
    }


def _run_service_checks():
    """Run all service checks and return services dict + overall status."""
    services = {
        'PostgreSQL': _check_database(),
        'Redis': _check_redis(),
        'Celery Workers': _check_celery(),
        'Celery Beat': _check_celery_beat(),
    }
    all_ok = all(s['status'] == 'ok' for s in services.values())
    has_error = any(s['status'] == 'error' for s in services.values())
    if all_ok:
        overall = 'ok'
    elif has_error:
        overall = 'error'
    else:
        overall = 'warn'

    result = {'services': services, 'all_ok': all_ok, 'overall': overall}
    # Cache for the header status indicator
    try:
        cache.set(STATUS_CACHE_KEY, json.dumps(result), STATUS_CACHE_TTL)
    except Exception:
        pass
    return result


@staff_member_required
def system_status(request):
    checks = _run_service_checks()

    admin_prefix = reverse('admin:index')

    links = [
        {'label': 'Reports', 'url': f'{admin_prefix}reports/report/'},
        {'label': 'User Reviews', 'url': f'{admin_prefix}reports/userreview/'},
        {'label': 'Periodic Tasks', 'url': f'{admin_prefix}django_celery_beat/periodictask/'},
        {'label': 'Task Results', 'url': f'{admin_prefix}django_celery_results/taskresult/'},
        {'label': 'API Health', 'url': '/api/health/'},
        {'label': 'API Docs', 'url': '/api/docs/'},
    ]

    from django.contrib import admin
    context = {
        **admin.site.each_context(request),
        'title': 'System Status',
        'services': checks['services'],
        'all_ok': checks['all_ok'],
        'metrics': _get_system_metrics(),
        'task_info': _get_recent_tasks(),
        'stats': _get_app_stats(),
        'links': links,
        'has_permission': True,
    }
    return render(request, 'admin/system_status.html', context)


@staff_member_required
def system_status_json(request):
    """Lightweight JSON endpoint for the admin header status indicator.

    Returns cached result from the last full dashboard load, or runs a
    fresh check if the cache is empty.
    """
    cached = cache.get(STATUS_CACHE_KEY)
    if cached:
        result = json.loads(cached)
    else:
        result = _run_service_checks()

    return JsonResponse({
        'overall': result['overall'],
        'services': {
            name: info['status']
            for name, info in result['services'].items()
        },
    })
