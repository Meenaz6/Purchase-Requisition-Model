from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class Picking(models.Model):
    _inherit = 'stock.picking'

    requisition_id = fields.Many2one('employee.requisition', string="Purchase Requisition")


    def action_confirm(self):
        """Override action_confirm to update requisition lines."""
        res = super(Picking, self).action_confirm()
        self._update_requisition_lines_state('confirmed')  # Update status to 'confirmed'
        return res


    def action_cancel(self):
        """Override action_cancel to update requisition lines."""
        res = super(Picking, self).action_cancel()
        self._update_requisition_lines_state('cancel')  # Update status to 'cancel'
        return res

    def button_validate(self):
        """Override button_validate to update requisition lines."""
        res = super(Picking, self).button_validate()
        self._update_requisition_lines_state('done')  # Update status to 'done'
        return res

    def _update_requisition_lines_state(self, new_state):
        """Update the status1 field in linked requisition lines."""
        for picking in self:
            # Fetch all requisition lines linked to this stock picking
            requisition_lines = self.env['purchase.requisition.line'].search(
                [('picking_id', '=', picking.id)]
            )
            # Update the `status1` field in the found requisition lines
            requisition_lines.write({'status': new_state})