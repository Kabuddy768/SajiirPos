from .models import AuditLog

def log_action(user, action, model_name, object_id, branch=None, before=None, after=None, notes=''):
    return AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        branch=branch,
        before_data=before,
        after_data=after,
        notes=notes
    )
