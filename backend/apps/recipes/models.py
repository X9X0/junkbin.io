"""
Recipe models for Junkbin.io

Community-submitted electronics project recipes with BOMs.
"""
import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


def recipe_image_path(instance, filename):
    """Generate upload path for recipe images."""
    ext = filename.split('.')[-1]
    new_filename = f'{uuid.uuid4().hex}.{ext}'
    return f'recipes/{instance.id}/{new_filename}'


class Recipe(models.Model):
    """
    A community-submitted electronics project recipe with a BOM.
    """

    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', _('Beginner')
        INTERMEDIATE = 'intermediate', _('Intermediate')
        ADVANCED = 'advanced', _('Advanced')
        EXPERT = 'expert', _('Expert')

    class Category(models.TextChoices):
        AUDIO = 'audio', _('Audio')
        POWER_SUPPLY = 'power_supply', _('Power Supply')
        IOT = 'iot', _('IoT')
        REPAIR = 'repair', _('Repair')
        LIGHTING = 'lighting', _('Lighting')
        TEST_EQUIPMENT = 'test_equipment', _('Test Equipment')
        RADIO = 'radio', _('Radio')
        COMPUTING = 'computing', _('Computing')
        ROBOTICS = 'robotics', _('Robotics')
        WEARABLE = 'wearable', _('Wearable')
        OTHER = 'other', _('Other')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=200,
        help_text=_('Recipe name')
    )
    slug = models.SlugField(
        max_length=300,
        unique=True,
        blank=True
    )
    description = models.TextField(
        help_text=_('Describe what this recipe builds and how')
    )
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        help_text=_('Difficulty level')
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        db_index=True,
        help_text=_('Project category')
    )
    external_url = models.URLField(
        blank=True,
        help_text=_('Link to project tutorial or instructions')
    )
    estimated_time = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Estimated build time, e.g. "2-3 hours"')
    )
    image = models.ImageField(
        upload_to=recipe_image_path,
        blank=True,
        null=True,
        help_text=_('Hero image for the recipe'),
        validators=[FileExtensionValidator(
            allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'webp']
        )]
    )

    # Ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_recipes'
    )

    # Moderation
    is_approved = models.BooleanField(
        default=False,
        help_text=_('Whether recipe has been approved')
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_('Featured on the recipes page')
    )

    # Denormalized stats
    component_count = models.PositiveSmallIntegerField(
        default=0,
        help_text=_('Number of required (non-optional) BOM items')
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times viewed')
    )
    build_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of builds (future use)')
    )

    # Full-text search
    search_vector = SearchVectorField(null=True, editable=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('recipe')
        verbose_name_plural = _('recipes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['difficulty', '-created_at']),
            models.Index(fields=['is_approved', '-created_at']),
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:250]
            slug = base_slug
            counter = 1
            while Recipe.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

        # Update search vector after save
        Recipe.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector('name', weight='A') +
                SearchVector('description', weight='B') +
                SearchVector('category', weight='C')
            )
        )

    def increment_view_count(self):
        """Increment view count (use F() to avoid race conditions)."""
        from django.db.models import F
        Recipe.objects.filter(pk=self.pk).update(view_count=F('view_count') + 1)

    def update_component_count(self):
        """Update denormalized component count (required items only)."""
        self.component_count = self.recipe_components.filter(
            is_optional=False
        ).count()
        self.save(update_fields=['component_count'])


class RecipeComponent(models.Model):
    """
    Junction table linking recipes to components (BOM line items).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_components'
    )
    component = models.ForeignKey(
        'components.Component',
        on_delete=models.CASCADE,
        related_name='recipe_components'
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        help_text=_('Number of this component needed')
    )
    notes = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Notes, e.g. "any value 100-470uF works"')
    )
    is_optional = models.BooleanField(
        default=False,
        help_text=_('Optional components excluded from match denominator')
    )

    class Meta:
        verbose_name = _('recipe component')
        verbose_name_plural = _('recipe components')
        ordering = ['component__manufacturer', 'component__part_number']
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'component'],
                name='unique_recipe_component'
            )
        ]

    def __str__(self):
        return f'{self.recipe.name} - {self.component}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.recipe.update_component_count()

    def delete(self, *args, **kwargs):
        recipe = self.recipe
        super().delete(*args, **kwargs)
        recipe.update_component_count()
