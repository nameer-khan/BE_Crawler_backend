# BaseModel and Mixins Usage Guide

## Overview

The `BaseModel` system provides a comprehensive set of mixins and base classes that add common functionality to Django models, including:

- **Soft Delete**: `is_active` and `deleted_at` fields
- **Timestamps**: `created_at` and `updated_at` fields
- **UUID Primary Keys**: Auto-generated UUID primary keys
- **Audit Fields**: `created_by` and `updated_by` fields
- **Status Management**: Status field with predefined choices
- **Utility Methods**: Common operations like soft delete, restore, etc.

## Available Base Classes

### 1. BaseModel
The main base class that includes all core functionality:

```python
from crawler.mixins import BaseModel

class MyModel(BaseModel):
    # Your model fields here
    pass
```

**Features:**
- UUID primary key
- Created/updated timestamps
- Soft delete capability
- Audit fields (created_by, updated_by)
- Status field
- Utility methods

### 2. BaseModelWithName
Extends BaseModel with name and description fields:

```python
from crawler.mixins import BaseModelWithName

class Category(BaseModelWithName):
    # Automatically includes name and description fields
    pass
```

### 3. BaseModelWithSlug
Extends BaseModelWithName with slug field:

```python
from crawler.mixins import BaseModelWithSlug

class Article(BaseModelWithSlug):
    # Automatically includes name, description, and slug fields
    pass
```

### 4. BaseModelWithOrdering
Extends BaseModelWithName with ordering field:

```python
from crawler.mixins import BaseModelWithOrdering

class MenuItem(BaseModelWithOrdering):
    # Automatically includes name, description, and order fields
    pass
```

## Individual Mixins

You can also use individual mixins for specific functionality:

### TimestampMixin
```python
from crawler.mixins import TimestampMixin

class MyModel(TimestampMixin, models.Model):
    # Only adds created_at and updated_at fields
    pass
```

### SoftDeleteMixin
```python
from crawler.mixins import SoftDeleteMixin

class MyModel(SoftDeleteMixin, models.Model):
    # Only adds soft delete functionality
    pass
```

### UUIDMixin
```python
from crawler.mixins import UUIDMixin

class MyModel(UUIDMixin, models.Model):
    # Only adds UUID primary key
    pass
```

## Usage Examples

### Basic Usage
```python
from crawler.mixins import BaseModel

class Product(BaseModel):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.name
```

### With Custom Status Choices
```python
from crawler.mixins import BaseModel

class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer_name = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Override the default status choices
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
```

### Soft Delete Operations
```python
# Create a product
product = Product.objects.create(name="Test Product", price=99.99)

# Soft delete (sets is_active=False and deleted_at timestamp)
product.delete()

# Check if deleted
print(product.is_active)  # False
print(product.deleted_at)  # Current timestamp

# Restore the product
product.restore()

# Permanently delete
product.hard_delete()

# Get only active objects
active_products = Product.active_objects.all()

# Get only deleted objects
deleted_products = Product.deleted_objects.all()
```

### Status Management
```python
# Get objects by status
pending_orders = Order.get_by_status('pending')
completed_orders = Order.get_by_status('delivered')

# Get all active objects
active_orders = Order.get_active_objects()
```

### Audit Fields
```python
# The created_by and updated_by fields are automatically managed
# You can set them manually if needed
from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.first()
product = Product.objects.create(
    name="New Product",
    created_by=user,
    updated_by=user
)
```

## Model Methods

### Soft Delete Methods
- `delete()`: Soft delete (sets `is_active=False`)
- `hard_delete()`: Permanently delete from database
- `restore()`: Restore soft-deleted object

### QuerySet Methods
- `active_objects`: Get only active objects
- `deleted_objects`: Get only soft-deleted objects
- `get_by_status(status)`: Get objects by status

### Utility Methods
- `get_active_objects()`: Class method to get active objects
- `get_by_status(status)`: Class method to get objects by status

## Database Queries

### Filtering Active Objects
```python
# Get only active products
active_products = Product.objects.filter(is_active=True)

# Or use the convenience method
active_products = Product.active_objects.all()
```

### Filtering by Status
```python
# Get products with specific status
pending_products = Product.objects.filter(status='pending', is_active=True)

# Or use the convenience method
pending_products = Product.get_by_status('pending')
```

### Including Deleted Objects
```python
# Get all products including deleted ones
all_products = Product.objects.all()  # Includes soft-deleted

# Get only deleted products
deleted_products = Product.deleted_objects.all()
```

## Migration Considerations

When adding BaseModel to existing models:

1. **Create a migration** to add the new fields
2. **Set default values** for existing records
3. **Update any existing queries** to use `active_objects` if needed

Example migration:
```python
# In your migration file
def set_defaults(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')
    MyModel.objects.all().update(
        is_active=True,
        status='active'
    )

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', 'previous_migration'),
    ]

    operations = [
        # Add fields
        migrations.AddField(
            model_name='mymodel',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        # ... other fields
        
        # Set defaults for existing records
        migrations.RunPython(set_defaults),
    ]
```

## Best Practices

### 1. Always Use active_objects for Queries
```python
# Good
products = Product.active_objects.all()

# Avoid (unless you specifically need deleted objects)
products = Product.objects.all()
```

### 2. Override Status Choices When Needed
```python
class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
```

### 3. Use Soft Delete for Data Integrity
```python
# Instead of hard deleting
# product.delete()  # This will soft delete

# Use hard delete only when necessary
product.hard_delete()  # This permanently removes
```

### 4. Leverage Utility Methods
```python
# Use convenience methods
pending_orders = Order.get_by_status('pending')
active_orders = Order.get_active_objects()

# Instead of manual queries
pending_orders = Order.objects.filter(status='pending', is_active=True)
```

## Performance Considerations

### Indexes
The BaseModel automatically adds indexes for:
- `is_active` field
- `created_at` field
- `updated_at` field

### Query Optimization
```python
# Use select_related for foreign keys
products = Product.active_objects.select_related('category').all()

# Use prefetch_related for many-to-many
orders = Order.active_objects.prefetch_related('items').all()
```

## Troubleshooting

### Common Issues

1. **Migration Errors**: Make sure to set default values for existing records
2. **Query Performance**: Use `active_objects` instead of filtering manually
3. **Soft Delete Not Working**: Ensure you're calling `delete()` on the instance, not the queryset

### Debug Queries
```python
# Check if soft delete is working
product = Product.objects.first()
print(f"Before delete: {product.is_active}")
product.delete()
print(f"After delete: {product.is_active}")

# Check active vs all objects
print(f"Active objects: {Product.active_objects.count()}")
print(f"All objects: {Product.objects.count()}")
```

This BaseModel system provides a robust foundation for Django models with common enterprise features while maintaining flexibility and performance.
