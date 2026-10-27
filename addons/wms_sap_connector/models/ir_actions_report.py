"""Override of ir.actions.report to enforce role-based access control for reports."""

import logging

import odoo
from odoo import _, api, models
from odoo.exceptions import AccessError

from ..constants import ERR_ONLY_DISPATCHER_CAN_PRINT_SURAT_JALAN

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    """Extends ir.actions.report to ensure report-level authorization checks."""

    _inherit = "ir.actions.report"

    def _check_report_security(self, report_ref):
        """Verifies that the calling user has permission to render the report if groups_id is set."""
        if (
            self.env.is_superuser()
            or self.env.user.id == odoo.SUPERUSER_ID
            or self.env.user.has_group("base.group_system")
        ):
            return

        report = self._get_report(report_ref)
        if report.groups_id:
            user_groups = self.env.user.groups_id
            if not (user_groups & report.groups_id):
                raise AccessError(_(ERR_ONLY_DISPATCHER_CAN_PRINT_SURAT_JALAN))

    @api.model
    def _render(self, report_ref, *args, **kwargs):
        self._check_report_security(report_ref)
        return super()._render(report_ref, *args, **kwargs)

    def _render_qweb_pdf(self, report_ref, *args, **kwargs):
        self._check_report_security(report_ref)
        return super()._render_qweb_pdf(report_ref, *args, **kwargs)

    def _render_qweb_html(self, report_ref, *args, **kwargs):
        self._check_report_security(report_ref)
        return super()._render_qweb_html(report_ref, *args, **kwargs)
