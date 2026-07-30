"""Custom template filters for the crime_map app."""

from django import template

register = template.Library()


@register.filter
def replace(value, arg):
    """Replace occurrences of a substring in a string.

    Usage: {{ "Hello World"|replace:"World,Universe" }}
    The argument should be "old,new".
    """
    if not value:
        return value
    parts = arg.split(",", 1)
    if len(parts) != 2:
        return value
    old, new = parts
    return str(value).replace(old, new)


@register.filter
def risk_class(level):
    """Convert a risk level string to a CSS class name.

    e.g. "Very Low" -> "very-low", "Very High" -> "very-high"
    """
    if not level:
        return ""
    return level.lower().replace(" ", "-")


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key.

    Usage: {{ my_dict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
