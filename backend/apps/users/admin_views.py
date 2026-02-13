"""
Admin views for bulk user contribution review.
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import User, AdminAuditLog
from apps.products.models import Product, ProductComment, ProductImage, Schematic
from apps.components.models import ProductComponent
from apps.submissions.models import Submission
from apps.reports.models import Report, UserReview


@staff_member_required
def user_contributions(request, user_id):
    """Display all contributions by a user for bulk review."""
    user = get_object_or_404(User, pk=user_id)

    # Querysets for actionable content
    submissions = Submission.objects.filter(
        submitted_by=user
    ).select_related('submitted_by').order_by('-submitted_at')

    product_components = ProductComponent.objects.filter(
        created_by=user
    ).select_related('product', 'component').order_by('-created_at')

    comments = ProductComment.objects.filter(
        author=user
    ).select_related('product').order_by('-created_at')

    images = ProductImage.objects.filter(
        uploaded_by=user
    ).select_related('product').order_by('-uploaded_at')

    # Read-only context
    products = Product.objects.filter(
        created_by=user
    ).order_by('-created_at')

    schematics = Schematic.objects.filter(
        uploaded_by=user
    ).select_related('product').order_by('-uploaded_at')

    reports = Report.objects.filter(
        reported_user=user
    ).order_by('-created_at')

    reviews = UserReview.objects.filter(
        user=user
    ).order_by('-created_at')

    # Summary counts
    summary = {
        'products': products.count(),
        'product_components': product_components.count(),
        'product_components_unverified': product_components.filter(is_verified=False).count(),
        'submissions': submissions.count(),
        'submissions_pending': submissions.filter(
            status__in=[Submission.Status.PENDING, Submission.Status.IN_REVIEW]
        ).count(),
        'comments': comments.count(),
        'images': images.count(),
        'schematics': schematics.count(),
        'reports': reports.count(),
        'reports_pending': reports.filter(status='pending').count(),
        'reviews': reviews.count(),
        'reviews_pending': reviews.filter(status='pending').count(),
    }

    context = {
        **admin.site.each_context(request),
        'title': f'Contribution Review: {user.username}',
        'reviewed_user': user,
        'summary': summary,
        'submissions': submissions[:50],
        'product_components': product_components[:50],
        'comments': comments[:50],
        'images': images[:50],
        'products': products[:50],
        'schematics': schematics[:50],
        'reports': reports[:50],
        'reviews': reviews[:50],
        'action_url': reverse('admin-user-contributions-action', args=[user.pk]),
    }
    return render(request, 'admin/user_contributions.html', context)


@staff_member_required
def user_contributions_action(request, user_id):
    """Process bulk actions on user contributions."""
    user = get_object_or_404(User, pk=user_id)
    redirect_url = reverse('admin-user-contributions', args=[user.pk])

    if request.method != 'POST':
        return redirect(redirect_url)

    action = request.POST.get('action', '')
    selected_ids = request.POST.getlist('selected_ids')

    if not selected_ids:
        messages.warning(request, 'No items selected.')
        return redirect(redirect_url)

    audit_details_base = {'via': 'user_contribution_review'}

    if action == 'verify_product_components':
        qs = ProductComponent.objects.filter(
            id__in=selected_ids, created_by=user, is_verified=False
        )
        count = qs.count()
        qs.update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now(),
        )
        for pc in ProductComponent.objects.filter(id__in=selected_ids, created_by=user):
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.COMPONENT_VERIFIED,
                pc,
                {**audit_details_base, 'product_component_id': str(pc.id)},
            )
        messages.success(request, f'Verified {count} component mapping(s).')

    elif action == 'approve_submissions':
        qs = Submission.objects.filter(
            id__in=selected_ids, submitted_by=user,
            status__in=[Submission.Status.PENDING, Submission.Status.IN_REVIEW],
        )
        count = 0
        for sub in qs:
            sub.approve(request.user, 'Bulk approved via contribution review')
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.SUBMISSION_APPROVED,
                sub,
                {**audit_details_base, 'submission_id': str(sub.id)},
            )
            count += 1
        messages.success(request, f'Approved {count} submission(s).')

    elif action == 'reject_submissions':
        qs = Submission.objects.filter(
            id__in=selected_ids, submitted_by=user,
            status__in=[Submission.Status.PENDING, Submission.Status.IN_REVIEW],
        )
        count = 0
        for sub in qs:
            sub.reject(request.user, 'Bulk rejected via contribution review')
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.SUBMISSION_REJECTED,
                sub,
                {**audit_details_base, 'submission_id': str(sub.id)},
            )
            count += 1
        messages.success(request, f'Rejected {count} submission(s).')

    elif action == 'delete_comments':
        qs = ProductComment.objects.filter(id__in=selected_ids, author=user)
        count = qs.count()
        for comment in qs:
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.OTHER,
                comment,
                {
                    **audit_details_base,
                    'action': 'comment_deleted',
                    'content_preview': comment.content[:100],
                },
            )
        qs.delete()
        messages.success(request, f'Deleted {count} comment(s).')

    elif action == 'delete_images':
        qs = ProductImage.objects.filter(id__in=selected_ids, uploaded_by=user)
        count = qs.count()
        for image in qs:
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.OTHER,
                image,
                {
                    **audit_details_base,
                    'action': 'image_deleted',
                    'product': str(image.product),
                },
            )
        qs.delete()
        messages.success(request, f'Deleted {count} image(s).')

    else:
        messages.error(request, f'Unknown action: {action}')

    return redirect(redirect_url)
