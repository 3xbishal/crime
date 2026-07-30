# Static Files

Place custom CSS, JavaScript, images, and fonts in this directory.

The project currently uses CDN links for Bootstrap and Leaflet.
If you want to self-host these assets, add them here and update the templates.

Example structure:
    static/
    ├── css/
    │   └── custom.css
    ├── js/
    │   └── custom.js
    └── images/
        └── favicon.ico

In templates, reference files with:
    {% load static %}
    <link rel="stylesheet" href="{% static 'css/custom.css' %}">
    <script src="{% static 'js/custom.js' %}"></script>
