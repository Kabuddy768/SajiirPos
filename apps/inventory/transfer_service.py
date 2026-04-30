import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import StockTransfer, StockTransferItem
from .services import StockService
from apps.audit.utils import log_action


class TransferError(Exception):
    pass


class TransferService:
    """
    Manages the full stock-transfer lifecycle:
        draft → approved → shipped → received
                                   ↘ cancelled (from draft or approved)

    Stock is deducted from the source branch on SHIP
    and added to the destination branch on RECEIVE.
    """

    # ------------------------------------------------------------------
    # CREATE  (draft)
    # ------------------------------------------------------------------
    @staticmethod
    def create(from_branch, to_branch, items_data, requested_by, notes=''):
        """
        items_data: list of dicts with:
            - product: Product instance
            - quantity: Decimal
            - batch: ProductBatch or None
        """
        if from_branch == to_branch:
            raise TransferError("Source and destination branch cannot be the same.")

        if not items_data:
            raise TransferError("Transfer must contain at least one item.")

        date_str = timezone.localtime().strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        transfer_number = (
            f"TRF-{from_branch.etims_branch_code or 'BR'}-"
            f"{to_branch.etims_branch_code or 'BR'}-{date_str}-{suffix}"
        )

        with transaction.atomic():
            transfer = StockTransfer.objects.create(
                transfer_number=transfer_number,
                from_branch=from_branch,
                to_branch=to_branch,
                status='draft',
                notes=notes,
                requested_by=requested_by,
            )

            for item in items_data:
                qty = Decimal(str(item['quantity']))
                if qty <= 0:
                    raise TransferError("Transfer quantity must be positive.")

                StockTransferItem.objects.create(
                    transfer=transfer,
                    product=item['product'],
                    quantity_requested=qty,
                    batch=item.get('batch'),
                )

            log_action(
                user=requested_by,
                action='transfer',
                model_name='StockTransfer',
                object_id=transfer.id,
                branch=from_branch,
                after={'transfer_number': transfer_number, 'status': 'draft'},
                notes=f"Created transfer to {to_branch.name}",
            )

        return transfer

    # ------------------------------------------------------------------
    # APPROVE
    # ------------------------------------------------------------------
    @staticmethod
    def approve(transfer, user):
        if transfer.status != 'draft':
            raise TransferError(f"Cannot approve — current status is '{transfer.status}'.")

        transfer.status = 'approved'
        transfer.approved_by = user
        transfer.approved_at = timezone.now()
        transfer.save()

        log_action(
            user=user,
            action='transfer',
            model_name='StockTransfer',
            object_id=transfer.id,
            branch=transfer.from_branch,
            after={'status': 'approved'},
            notes=f"Approved by {user.email}",
        )
        return transfer

    # ------------------------------------------------------------------
    # SHIP  — deducts stock from source branch
    # ------------------------------------------------------------------
    @staticmethod
    def ship(transfer, user, shipped_quantities=None):
        """
        shipped_quantities: optional dict {transfer_item_id: Decimal}
        If not provided, ships full requested quantity for every item.
        """
        if transfer.status != 'approved':
            raise TransferError(f"Cannot ship — current status is '{transfer.status}'.")

        with transaction.atomic():
            for item in transfer.items.select_related('product'):
                qty_to_ship = (
                    Decimal(str(shipped_quantities[item.id]))
                    if shipped_quantities and item.id in shipped_quantities
                    else item.quantity_requested
                )

                if qty_to_ship <= 0:
                    raise TransferError(f"Ship quantity for {item.product.name} must be positive.")

                # Deduct from source branch
                StockService.adjust(
                    product=item.product,
                    branch=transfer.from_branch,
                    quantity=-qty_to_ship,
                    reason='transfer_out',
                    reference_id=transfer.transfer_number,
                    user=user,
                    batch=item.batch,
                    notes=f"Shipped to {transfer.to_branch.name}",
                )

                item.quantity_shipped = qty_to_ship
                item.save()

            transfer.status = 'shipped'
            transfer.shipped_by = user
            transfer.shipped_at = timezone.now()
            transfer.save()

            log_action(
                user=user,
                action='transfer',
                model_name='StockTransfer',
                object_id=transfer.id,
                branch=transfer.from_branch,
                after={'status': 'shipped'},
                notes=f"Shipped by {user.email}",
            )

        return transfer

    # ------------------------------------------------------------------
    # RECEIVE  — adds stock to destination branch
    # ------------------------------------------------------------------
    @staticmethod
    def receive(transfer, user, received_quantities=None):
        """
        received_quantities: optional dict {transfer_item_id: Decimal}
        If not provided, receives full shipped quantity for every item.
        """
        if transfer.status != 'shipped':
            raise TransferError(f"Cannot receive — current status is '{transfer.status}'.")

        with transaction.atomic():
            for item in transfer.items.select_related('product'):
                qty_to_receive = (
                    Decimal(str(received_quantities[item.id]))
                    if received_quantities and item.id in received_quantities
                    else item.quantity_shipped
                )

                if qty_to_receive < 0:
                    raise TransferError(f"Receive quantity for {item.product.name} cannot be negative.")

                # Add to destination branch
                StockService.adjust(
                    product=item.product,
                    branch=transfer.to_branch,
                    quantity=qty_to_receive,
                    reason='transfer_in',
                    reference_id=transfer.transfer_number,
                    user=user,
                    batch=item.batch,
                    notes=f"Received from {transfer.from_branch.name}",
                )

                item.quantity_received = qty_to_receive
                item.save()

            transfer.status = 'received'
            transfer.received_by = user
            transfer.received_at = timezone.now()
            transfer.save()

            log_action(
                user=user,
                action='transfer',
                model_name='StockTransfer',
                object_id=transfer.id,
                branch=transfer.to_branch,
                after={'status': 'received'},
                notes=f"Received by {user.email}",
            )

        return transfer

    # ------------------------------------------------------------------
    # CANCEL  — only from draft or approved
    # ------------------------------------------------------------------
    @staticmethod
    def cancel(transfer, user):
        if transfer.status not in ('draft', 'approved'):
            raise TransferError(
                f"Cannot cancel — status is '{transfer.status}'. "
                "Only draft or approved transfers can be cancelled."
            )

        transfer.status = 'cancelled'
        transfer.save()

        log_action(
            user=user,
            action='transfer',
            model_name='StockTransfer',
            object_id=transfer.id,
            branch=transfer.from_branch,
            after={'status': 'cancelled'},
            notes=f"Cancelled by {user.email}",
        )
        return transfer
