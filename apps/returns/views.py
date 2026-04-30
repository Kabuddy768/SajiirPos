from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from apps.tenants.permissions import IsCashier
from apps.sales.models import Sale
from .models import Return
from .serializers import ReturnSerializer, ReturnCreateSerializer
from .services import ReturnService, ReturnApprovalRequired, InvalidReturnError

User = get_user_model()


class ReturnViewSet(viewsets.ModelViewSet):
    queryset = Return.objects.select_related(
        'original_sale', 'branch', 'processed_by', 'approved_by'
    ).prefetch_related('items__sale_item__product').all()
    serializer_class = ReturnSerializer
    permission_classes = [IsAuthenticated, IsCashier]

    def create(self, request, *args, **kwargs):
        serializer = ReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve original sale
        try:
            original_sale = Sale.objects.get(id=data['original_sale_id'])
        except Sale.DoesNotExist:
            return Response(
                {'error': f"Sale {data['original_sale_id']} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Resolve approver (if provided)
        approved_by = None
        if data.get('approved_by_id'):
            try:
                approved_by = User.objects.get(id=data['approved_by_id'])
            except User.DoesNotExist:
                return Response(
                    {'error': 'Approver user not found.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            return_obj = ReturnService.process(
                original_sale=original_sale,
                items_data=data['items'],
                reason=data['reason'],
                refund_method=data['refund_method'],
                cashier=request.user,
                approved_by=approved_by,
                notes=data.get('notes', ''),
            )
        except ReturnApprovalRequired as e:
            return Response(
                {'error': str(e), 'code': 'approval_required'},
                status=status.HTTP_403_FORBIDDEN,
            )
        except InvalidReturnError as e:
            return Response(
                {'error': str(e), 'code': 'invalid_return'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ReturnSerializer(return_obj).data,
            status=status.HTTP_201_CREATED,
        )
