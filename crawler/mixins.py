"""
Django model mixins for common functionality.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Custom managers
class ActiveManager(models.Manager):
    """
    Custom manager that only returns active (non-deleted) objects.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class DeletedManager(models.Manager):
    """
    Custom manager that only returns soft-deleted objects.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=False)


class TimestampMixin(models.Model):
    """
    Mixin to add created_at and updated_at fields to models.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("Timestamp when the record was created")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Timestamp when the record was last updated")
    )

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Mixin to add soft delete functionality to models.
    """
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether this record is active (not soft deleted)")
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Deleted At"),
        help_text=_("Timestamp when the record was soft deleted")
    )

    # Custom managers
    objects = models.Manager()
    active_objects = ActiveManager()
    deleted_objects = DeletedManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the record."""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the record."""
        super().delete(using, keep_parents)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=['is_active', 'deleted_at'])


class AuditMixin(models.Model):
    """
    Mixin to add audit fields to models.
    """
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name=_("Created By"),
        help_text=_("User who created this record")
    )
    updated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name=_("Updated By"),
        help_text=_("User who last updated this record")
    )

    class Meta:
        abstract = True


class StatusMixin(models.Model):
    """
    Mixin to add status field to models.
    """
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_("Status"),
        help_text=_("Current status of the record")
    )

    class Meta:
        abstract = True


class OrderingMixin(models.Model):
    """
    Mixin to add ordering field to models.
    """
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Ordering position")
    )

    class Meta:
        abstract = True
        ordering = ['order']


class SlugMixin(models.Model):
    """
    Mixin to add slug field to models.
    """
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("URL-friendly identifier")
    )

    class Meta:
        abstract = True


class DescriptionMixin(models.Model):
    """
    Mixin to add description field to models.
    """
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description of the record")
    )

    class Meta:
        abstract = True


class NameMixin(models.Model):
    """
    Mixin to add name field to models.
    """
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        help_text=_("Name of the record")
    )

    class Meta:
        abstract = True


# Base model combinations
class BaseModel(TimestampMixin, SoftDeleteMixin, AuditMixin, StatusMixin):
    """
    Base model with common fields and functionality.
    """
    class Meta:
        abstract = True


class BaseModelWithName(BaseModel, NameMixin):
    """
    Base model with name field.
    """
    class Meta:
        abstract = True


class BaseModelWithSlug(BaseModel, SlugMixin):
    """
    Base model with slug field.
    """
    class Meta:
        abstract = True


class BaseModelWithOrdering(BaseModel, OrderingMixin):
    """
    Base model with ordering field.
    """
    class Meta:
        abstract = True


# Utility mixins for specific use cases
class CacheMixin(models.Model):
    """
    Mixin to add caching capabilities to models.
    """
    
    class Meta:
        abstract = True

    def get_cache_key(self, suffix=''):
        """
        Generate a cache key for this instance.
        """
        return f"{self.__class__.__name__}:{self.id}:{suffix}"

    def clear_cache(self):
        """
        Clear cache for this instance.
        """
        from django.core.cache import cache
        cache.delete(self.get_cache_key())


class ValidationMixin(models.Model):
    """
    Mixin to add validation methods to models.
    """
    
    class Meta:
        abstract = True

    def clean(self):
        """
        Custom validation logic.
        """
        super().clean()
        self.validate_custom_fields()

    def validate_custom_fields(self):
        """
        Override this method to add custom validation logic.
        """
        pass

    def save(self, *args, **kwargs):
        """
        Save with validation.
        """
        self.full_clean()
        super().save(*args, **kwargs)


class SearchMixin(models.Model):
    """
    Mixin to add search functionality to models.
    """
    
    class Meta:
        abstract = True

    @classmethod
    def search(cls, query, fields=None):
        """
        Search in specified fields.
        """
        if not fields:
            fields = ['name', 'description']
        
        q_objects = models.Q()
        for field in fields:
            if hasattr(cls, field):
                q_objects |= models.Q(**{f"{field}__icontains": query})
        
        return cls.objects.filter(q_objects, is_active=True)


class ExportMixin(models.Model):
    """
    Mixin to add export functionality to models.
    """
    
    class Meta:
        abstract = True

    def to_dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
        }

    def to_json(self):
        """
        Convert model instance to JSON.
        """
        import json
        from django.core.serializers.json import DjangoJSONEncoder
        return json.dumps(self.to_dict(), cls=DjangoJSONEncoder)
