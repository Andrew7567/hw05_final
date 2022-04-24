from django.shortcuts import render


def page_not_found(request, exception):
    template = 'core/404.html'
    # Переменная exception содержит отладочную информацию;
    # выводить её в шаблон пользовательской страницы 404 мы не станем
    return render(request, template, {'path': request.path}, status=404)


def csrf_failure(request, reason=''):
    template = 'core/403csrf.html'
    return render(request, template, {'path': request.path}, status=403)


def server_error(request, reason=''):
    template = 'core/500.html'
    return render(request, template, {'path': request.path}, status=500)
