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
    cpu = psutil.cpu_percent(interval=2)
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


def _fmt_age(seconds):
    if seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    return f"{int(seconds / 86400)}d ago"


def _summarize_cmd(cmdline):
    if not cmdline:
        return ''
    cmd = ' '.join(cmdline)
    return cmd[:80] + ('...' if len(cmd) > 80 else '')


def _sample_processes():
    """Sample all processes: CPU% over 1s window + memory. Returns list of dicts."""
    import time
    total_ram = psutil.virtual_memory().total
    candidates = list(psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']))
    for p in candidates:
        try:
            p.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(1)
    results = []
    for p in candidates:
        try:
            cpu = p.cpu_percent()
            info = p.info
            rss = info['memory_info'].rss if info.get('memory_info') else 0
            results.append({
                'pid': p.pid,
                'name': info['name'] or '?',
                'cpu': round(cpu, 1),
                'mem_mb': round(rss / 1024 / 1024, 1),
                'mem_percent': round(rss / total_ram * 100, 1),
                'cmd': _summarize_cmd(info.get('cmdline') or []),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return results


def _get_top_cpu_processes(n=5):
    """Return top N processes sorted by CPU%."""
    return sorted(_sample_processes(), key=lambda x: x['cpu'], reverse=True)[:n]


def _get_active_celery_tasks():
    """Return active Celery task names, excluding the health check itself."""
    try:
        active = current_app.control.inspect(timeout=1).active() or {}
        tasks = []
        for worker_tasks in active.values():
            for task in worker_tasks:
                name = task.get('name', '')
                if 'check_system_health' not in name:
                    tasks.append(name)
        return tasks
    except Exception:
        return []


def _get_top_mem_processes(n=5):
    """Return top N processes sorted by RSS memory."""
    return sorted(_sample_processes(), key=lambda x: x['mem_mb'], reverse=True)[:n]


def _get_swap_info():
    """Return swap usage dict, or None if no swap configured."""
    swap = psutil.swap_memory()
    if swap.total == 0:
        return None
    return {
        'used': _fmt_bytes(swap.used),
        'total': _fmt_bytes(swap.total),
        'percent': round(swap.percent, 1),
    }


def _get_recent_large_files(search_dirs=None, min_size_mb=50, hours=24):
    """Return files >= min_size_mb modified in the last `hours` hours, largest first."""
    import os
    import time as _time
    if search_dirs is None:
        search_dirs = ['/app', '/tmp']
    cutoff = _time.time() - hours * 3600
    results = []
    for base in search_dirs:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules'}]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    st = os.stat(fpath)
                    size_mb = st.st_size / 1024 / 1024
                    if size_mb >= min_size_mb and st.st_mtime >= cutoff:
                        results.append({
                            'path': fpath,
                            'size': _fmt_bytes(st.st_size),
                            'size_mb': size_mb,
                            'age': _fmt_age(_time.time() - st.st_mtime),
                        })
                except OSError:
                    pass
    return sorted(results, key=lambda x: x['size_mb'], reverse=True)[:10]


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
        {'label': 'Grafana (admin / GRAFANA_ADMIN_PASSWORD)', 'url': '/grafana/', 'external': True},
        {'label': 'Prometheus', 'url': '/prometheus/', 'external': True},
        {'label': 'Search Queries', 'url': f'{admin_prefix}api/searchquery/'},
        {'label': 'Component Views', 'url': f'{admin_prefix}components/componentviewstats/'},
        {'label': 'Reports', 'url': f'{admin_prefix}reports/report/'},
        {'label': 'User Reviews', 'url': f'{admin_prefix}reports/userreview/'},
        {'label': 'Periodic Tasks', 'url': f'{admin_prefix}django_celery_beat/periodictask/'},
        {'label': 'Task Results', 'url': f'{admin_prefix}django_celery_results/taskresult/'},
        {'label': 'API Health', 'url': '/api/health/', 'external': True},
        {'label': 'API Docs', 'url': '/api/docs/', 'external': True},
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
