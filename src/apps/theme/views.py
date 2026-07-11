from django.shortcuts import render


def style_guide(request):
    """
    Return our style guide template for reference
    """
    return render(request, "style-guide.html")
