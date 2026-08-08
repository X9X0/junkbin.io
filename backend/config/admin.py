"""
Custom admin site for Junkbin.io.

Reorganizes the sidebar into logical groups and condensed sections.
"""
from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


# Defines how sidebar groups are organized.
# Keys are display names, values are lists of (app_label, model_name) tuples.
# Models not listed here go into an "Other" group at the bottom.
SIDEBAR_GROUPS = {
    'Content': [
        ('products', 'product'),
        ('components', 'component'),
        ('components', 'productcomponent'),
        ('products', 'schematic'),
        ('products', 'firmware'),
        ('products', 'productimage'),
        ('components', 'componentimage'),
        ('components', 'componentdatasheet'),
        ('components', 'componenttypeimage'),
    ],
    'Community': [
        ('products', 'productcomment'),
        ('submissions', 'submission'),
        ('submissions', 'submissioncomment'),
        ('newsletter', 'subscriber'),
    ],
    'Moderation': [
        ('reports', 'report'),
        ('reports', 'userreview'),
    ],
    'Users': [
        ('users', 'user'),
        ('users', 'useractivity'),
        ('users', 'adminauditlog'),
        ('auth', 'group'),
    ],
    'System': [
        ('api', 'notificationpreference'),
        ('api', 'notificationlog'),
        ('django_celery_beat', 'periodictask'),
        ('django_celery_results', 'taskresult'),
        ('axes', 'accessattempt'),
        ('axes', 'accesslog'),
        ('axes', 'accessfailurelog'),
    ],
    'Analytics': [
        ('api', 'searchquery'),
        ('components', 'componentviewstats'),
    ],
}

# No models are hidden — everything shows under "Other" if not in a group above
HIDDEN_MODELS = set()


class JunkbinAdminSite(AdminSite):
    site_header = 'Junkbin.io Administration'
    site_title = 'Junkbin.io Admin'
    index_title = 'Dashboard'

    def get_app_list(self, request, app_label=None):
        """Reorganize the app list into logical sidebar groups."""
        original = super().get_app_list(request, app_label)

        # If viewing a specific app, return the default
        if app_label:
            return original

        # Build a lookup: (app_label, model_name) -> model_dict
        model_lookup = {}
        app_urls = {}
        for app in original:
            al = app['app_label']
            app_urls[al] = app.get('app_url', '')
            for model in app.get('models', []):
                mn = model['object_name'].lower()
                model_lookup[(al, mn)] = model

        # Build grouped app list
        grouped = []
        used = set()

        for group_name, members in SIDEBAR_GROUPS.items():
            models = []
            for key in members:
                if key in model_lookup and key not in HIDDEN_MODELS:
                    models.append(model_lookup[key])
                    used.add(key)
            if models:
                grouped.append({
                    'name': group_name,
                    'app_label': group_name.lower(),
                    'app_url': '',
                    'has_module_perms': True,
                    'models': models,
                })

        # Collect any remaining models not in a group and not hidden
        other_models = []
        for app in original:
            al = app['app_label']
            for model in app.get('models', []):
                mn = model['object_name'].lower()
                key = (al, mn)
                if key not in used and key not in HIDDEN_MODELS:
                    other_models.append(model)
                    used.add(key)

        if other_models:
            grouped.append({
                'name': 'Other',
                'app_label': 'other',
                'app_url': '',
                'has_module_perms': True,
                'models': other_models,
            })

        return grouped


class JunkbinAdminConfig(AdminConfig):
    default_site = 'config.admin.JunkbinAdminSite'
