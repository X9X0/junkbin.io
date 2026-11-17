"""
eBay's marketplace account deletion notifications. The eBay developer program turns a production keyset on only
once the application has an HTTPS endpoint that (1) answers eBay's challenge and (2) accepts the notifications
eBay sends when an eBay user closes their account. The site keeps no eBay user data (the Browse API lane reads
public listing titles), so a notification needs nothing beyond an acknowledgement.

    GET  /api/ebay/account-deletion/?challenge_code=...   -> {"challengeResponse": sha256(code + token + endpoint url)}
    POST /api/ebay/account-deletion/                       -> 200 (the body is logged, nothing to delete)

The token is EBAY_VERIFICATION_TOKEN in .env, the same string entered in the developer portal with the endpoint URL
(settings.SITE_URL + this path). Without a token the endpoint answers 404.
"""
import hashlib
import logging

from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView

log = logging.getLogger(__name__)


class EbayAccountDeletionView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []                      # eBay's challenge must never meet a 429

    def get(self, request):
        token = settings.EBAY_VERIFICATION_TOKEN
        code = request.GET.get('challenge_code', '')
        if not token or not code:
            return JsonResponse({'detail': 'not found'}, status=404)
        endpoint = settings.SITE_URL.rstrip('/') + request.path
        digest = hashlib.sha256((code + token + endpoint).encode()).hexdigest()
        return JsonResponse({'challengeResponse': digest})

    def post(self, request):
        if not settings.EBAY_VERIFICATION_TOKEN:
            return JsonResponse({'detail': 'not found'}, status=404)
        data = request.data if isinstance(request.data, dict) else {}
        meta = data.get('metadata', {}) if isinstance(data.get('metadata'), dict) else {}
        log.info('ebay account deletion notification: topic=%s id=%s', meta.get('topic'), data.get('notificationId'))
        return JsonResponse({}, status=200)
