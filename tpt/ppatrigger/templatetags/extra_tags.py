from django import template
register = template.Library()

@register.filter
def project_has_category(project, category_id):
    """Returns non zero value if a project has the category.
    Usage::

        {% if project | project_has_category:category.id %}
        ...
        {% endif %}
    """
    return project.categories.filter(id=category_id).count()
