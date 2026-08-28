"""
Tests for delegate message forwarding (User.forward_messages_to).
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.messaging.models import Message
from apps.users.tests.factories import UserFactory


def authed_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def send(user, **payload):
    return authed_client(user).post(reverse('message-send'), payload)


@pytest.mark.django_db
class TestForwardOnReceive:
    def test_message_to_delegate_admin_is_mirrored_to_delegate(self):
        admin = UserFactory()
        delegate = UserFactory()
        sender = UserFactory()
        admin.forward_messages_to = delegate
        admin.save(update_fields=['forward_messages_to'])

        resp = send(sender, recipient_id=str(admin.pk), content='hi admin')
        assert resp.status_code == status.HTTP_201_CREATED

        mirrored = Message.objects.get(sender=admin, content__icontains='hi admin')
        assert sender.username in mirrored.content
        assert mirrored.forwarded_from_conversation is not None

        shadow = mirrored.conversation
        assert {shadow.participant_1_id, shadow.participant_2_id} == {admin.pk, delegate.pk}

        # Admin's own inbox is untouched - the original message is still there.
        original = Message.objects.get(sender=sender, content='hi admin')
        assert {original.conversation.participant_1_id, original.conversation.participant_2_id} == {admin.pk, sender.pk}

    def test_no_forward_when_delegate_not_set(self):
        admin = UserFactory()
        sender = UserFactory()

        resp = send(sender, recipient_id=str(admin.pk), content='hi')
        assert resp.status_code == status.HTTP_201_CREATED

        # Only the one real message exists - no mirrored copy anywhere.
        assert Message.objects.count() == 1

    def test_no_forward_when_delegate_inactive(self):
        admin = UserFactory()
        delegate = UserFactory(is_active=False)
        sender = UserFactory()
        admin.forward_messages_to = delegate
        admin.save(update_fields=['forward_messages_to'])

        send(sender, recipient_id=str(admin.pk), content='hi')

        assert Message.objects.count() == 1

    def test_no_forward_when_sender_is_the_delegate(self):
        """The delegate messaging admin directly isn't a fresh thing to mirror."""
        admin = UserFactory()
        delegate = UserFactory()
        admin.forward_messages_to = delegate
        admin.save(update_fields=['forward_messages_to'])

        resp = send(delegate, recipient_id=str(admin.pk), content='hey boss')
        assert resp.status_code == status.HTTP_201_CREATED

        # No mirrored copy is created since there's nothing to relay yet.
        assert Message.objects.filter(forwarded_from_conversation__isnull=False).count() == 0


@pytest.mark.django_db
class TestDelegateReplyRelay:
    def test_delegate_reply_relays_back_to_original_sender(self):
        admin = UserFactory()
        delegate = UserFactory()
        sender = UserFactory()
        admin.forward_messages_to = delegate
        admin.save(update_fields=['forward_messages_to'])

        send(sender, recipient_id=str(admin.pk), content='need help')
        original_conversation = Message.objects.filter(sender=sender).first().conversation
        shadow_conversation = Message.objects.filter(sender=admin).first().conversation

        reply = send(delegate, conversation_id=str(shadow_conversation.pk), content='sure, one sec')
        assert reply.status_code == status.HTTP_201_CREATED

        relayed = Message.objects.filter(
            conversation=original_conversation, sender=admin, content='sure, one sec'
        )
        assert relayed.exists()
        # The original sender never sees the delegate's identity.
        assert not Message.objects.filter(conversation=original_conversation, sender=delegate).exists()

    def test_reply_routes_to_most_recently_forwarded_thread(self):
        admin = UserFactory()
        delegate = UserFactory()
        sender_a = UserFactory()
        sender_b = UserFactory()
        admin.forward_messages_to = delegate
        admin.save(update_fields=['forward_messages_to'])

        send(sender_a, recipient_id=str(admin.pk), content='from A')
        send(sender_b, recipient_id=str(admin.pk), content='from B')
        shadow_conversation = Message.objects.filter(sender=admin).first().conversation

        send(delegate, conversation_id=str(shadow_conversation.pk), content='reply')

        conv_b = Message.objects.filter(sender=sender_b).first().conversation
        conv_a = Message.objects.filter(sender=sender_a).first().conversation
        assert Message.objects.filter(conversation=conv_b, sender=admin, content='reply').exists()
        assert not Message.objects.filter(conversation=conv_a, sender=admin, content='reply').exists()

    def test_delegate_message_with_no_prior_forward_is_not_relayed(self):
        """Delegate messaging admin out of the blue, with nothing forwarded yet."""
        admin = UserFactory()
        delegate = UserFactory()
        admin.forward_messages_to = delegate
        admin.save(update_fields=['forward_messages_to'])

        resp = send(delegate, recipient_id=str(admin.pk), content='hello there')
        assert resp.status_code == status.HTTP_201_CREATED
        assert Message.objects.count() == 1


@pytest.mark.django_db
class TestForwardValidation:
    def test_cannot_set_self_as_delegate_via_api(self):
        admin = UserFactory()
        resp = authed_client(admin).patch(
            reverse('current-user'), {'forward_messages_to': str(admin.pk)}
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_can_set_and_clear_delegate_via_api(self):
        admin = UserFactory()
        delegate = UserFactory()

        resp = authed_client(admin).patch(
            reverse('current-user'), {'forward_messages_to': str(delegate.pk)}
        )
        assert resp.status_code == status.HTTP_200_OK
        admin.refresh_from_db()
        assert admin.forward_messages_to_id == delegate.pk

        resp = authed_client(admin).patch(
            reverse('current-user'), {'forward_messages_to': None}, format='json'
        )
        assert resp.status_code == status.HTTP_200_OK
        admin.refresh_from_db()
        assert admin.forward_messages_to_id is None
