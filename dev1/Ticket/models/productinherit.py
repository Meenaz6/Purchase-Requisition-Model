from odoo import api, fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one('employee.requisition', string="Purchase Requisition")

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        if 'state' in vals:
            status_mapping = {
                'draft': 'rfq',
                'sent': 'sent',
                'purchase': 'purchase',
                'done': 'done',
                'cancel': 'cancel',
            }
            new_status = status_mapping.get(vals['state'])
            if new_status:
                for order in self:
                    requisition = order.requisition_id
                    if requisition:
                        requisition_lines = requisition.line_ids.filtered(
                            lambda line: line.product_id in order.order_line.mapped('product_id')
                        )
                        requisition_lines.write({'status': new_status})
        return res