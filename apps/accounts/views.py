from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages

from apps.tenants.permissions import get_user_role
from apps.tenants.redirects import get_post_login_url

User = get_user_model()


def login_step1(request):
    """
    Step 1: collect email.  Only confirms the email exists in a generic way.
    We never reveal whether the email is registered (OWASP best practice).
    """
    if request.user.is_authenticated:
        return redirect(get_post_login_url(request))

    error = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            error = 'Please enter your email address.'
        else:
            # Store email in session and move to step 2
            request.session['login_email'] = email
            return redirect('login_password')

    return render(request, 'accounts/login_email.html', {
        'error': error,
        'email_value': request.POST.get('email', ''),
    })


def login_step2(request):
    """
    Step 2: collect password and authenticate.
    On success, redirect by role.
    """
    if request.user.is_authenticated:
        return redirect(get_post_login_url(request))

    email = request.session.get('login_email', '')
    if not email:
        return redirect('login')

    error = None

    if request.method == 'POST':
        email = request.POST.get('email', email).strip().lower()
        password = request.POST.get('password', '')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            # Clear the session key
            request.session.pop('login_email', None)
            return redirect(get_post_login_url(request))
        else:
            # Generic message — never say which field is wrong
            error = 'Invalid email or password. Please try again.'

    return render(request, 'accounts/login_password.html', {
        'email': email,
        'error': error,
    })
