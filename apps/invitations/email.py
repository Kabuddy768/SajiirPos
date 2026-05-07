from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


def send_invitation_email(invitation, request):
    """
    Send the invitation email to the invitee with a tokenised accept link.
    """
    accept_url = request.build_absolute_uri(
        reverse('invite_accept') + f'?token={invitation.token}'
    )

    tenant_name = getattr(request, 'tenant', None)
    tenant_name = tenant_name.name if tenant_name else 'Sajiir POS'
    role_display = invitation.get_role_display()

    subject = f"You've been invited to join {tenant_name} as {role_display}"

    plain_body = (
        f"Hi,\n\n"
        f"{invitation.invited_by.get_full_name() or invitation.invited_by.email} has invited you "
        f"to join {tenant_name} as a {role_display}.\n\n"
        f"Click the link below to accept your invitation (valid for 48 hours):\n"
        f"{accept_url}\n\n"
        f"If you did not expect this invitation, you can safely ignore this email.\n\n"
        f"— The {tenant_name} Team"
    )

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#0f172a; color:#cbd5e1; margin:0; padding:0; }}
    .container {{ max-width:560px; margin:40px auto; background:#1e293b; border-radius:12px; overflow:hidden; }}
    .header {{ background:linear-gradient(135deg,#4f46e5,#6366f1); padding:32px 40px; }}
    .header h1 {{ margin:0; color:#fff; font-size:22px; font-weight:700; }}
    .header p {{ margin:4px 0 0; color:#c7d2fe; font-size:13px; }}
    .body {{ padding:32px 40px; }}
    .body p {{ margin:0 0 16px; font-size:15px; line-height:1.6; color:#94a3b8; }}
    .body strong {{ color:#e2e8f0; }}
    .btn {{ display:inline-block; margin:24px 0 8px; padding:14px 28px; background:#4f46e5; color:#fff !important;
            font-weight:600; font-size:15px; border-radius:8px; text-decoration:none; }}
    .btn:hover {{ background:#4338ca; }}
    .footer {{ padding:20px 40px; border-top:1px solid #334155; font-size:12px; color:#475569; }}
    .expiry {{ background:#0f172a; border-radius:8px; padding:12px 16px; font-size:13px; color:#64748b; margin-top:20px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>You're Invited! 🎉</h1>
      <p>{tenant_name} · Staff Invitation</p>
    </div>
    <div class="body">
      <p>Hi,</p>
      <p>
        <strong>{invitation.invited_by.get_full_name() or invitation.invited_by.email}</strong>
        has invited you to join <strong>{tenant_name}</strong> as a <strong>{role_display}</strong>.
      </p>
      <a href="{accept_url}" class="btn">Accept Invitation →</a>
      <div class="expiry">⏳ This invitation expires in 48 hours.</div>
    </div>
    <div class="footer">
      If you did not expect this invitation, you can safely ignore this email.
    </div>
  </div>
</body>
</html>
"""

    send_mail(
        subject=subject,
        message=plain_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sajiir.co.ke'),
        recipient_list=[invitation.email],
        html_message=html_body,
        fail_silently=False,
    )
