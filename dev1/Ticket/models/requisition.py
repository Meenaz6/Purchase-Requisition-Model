from docutils.nodes import reference
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date, timedelta
from odoo.exceptions import UserError
from collections import defaultdict

class EmployeeRequisition(models.Model):
    _name = 'employee.requisition'
    _description = 'Purchase Requisition'
    _rec_name = 'reference'

    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Requisition Lines')
    reference = fields.Char(default='New', readonly=True)
    purchase_order_ids = fields.One2many('purchase.order', 'requisition_id', string='Linked Purchase Orders')
    stock_picking_ids = fields.One2many('stock.picking', 'requisition_id', string="Stock Picking")
    requested_by = fields.Many2one('res.users', string='Requested By',
                                   default=lambda self: self.env.user,  # Set the default value to the current user
                                   domain=lambda self: [('id', '=', self.env.user.id)])  # Restrict the dropdown to only the current user
    project = fields.Many2one('project.project', string='Project Name')
    department = fields.Many2one('hr.department', string='Department')
    company = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,  # Set the default value to the current company
                                   domain=lambda self: [('id', '=', self.env.company.id)])  # Restrict the dropdown to only the current company
    requi_responsible = fields.Many2one('hr.employee', string='Requisition Responsible')
    requisition_date = fields.Date(string='Requisition Date', default=fields.Date.context_today)
    requisition_deadline = fields.Date(string='Requisition Deadline')
    Information = fields.Text(string="Information")
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('partially', 'Partially Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ], string='Status', default='draft')
    destination_location_id = fields.Many2one('stock.location', string="Destination Location")
    internal_picking_location_id = fields.Many2one('stock.location', string="Internal Picking Location")
    all_lines_completed = fields.Boolean(string='All Lines Completed', compute='_compute_all_lines_completed', store=True)
    all_internal_completed = fields.Boolean(string='All Internal Completed', compute='_compute_all_internal_completed', store=True)
    partially_requisition = fields.Integer(compute="_compute_requisition", string="Partially PR", store=True)
    total_requisitions = fields.Integer(compute="_compute_requisition", string="Total Requisitions", store=True)
    submitted_requisition = fields.Integer(compute="_compute_requisition", string="Submitted PR", store=True)
    approved_requisition = fields.Integer(compute="_compute_requisition", string="Approved PR", store=True)
    completed_requisition = fields.Integer(compute="_compute_requisition", string="Completed PR", store=True)
    rejected_requisition = fields.Integer(compute="_compute_requisition", string="Rejected PR", store=True)
    total_lines = fields.Integer(compute="_compute_requisition_lines", string="Total lines", store=True)

    @api.depends('state')
    def _compute_requisition(self):
        """Compute requisition counts only once to improve performance."""
        state_counts = defaultdict(int)

        # Compute count for all states at once
        all_records = self.sudo().search([])  # Fetch all records once
        state_counts['total'] = len(all_records)  # Total requisitions

        for rec in all_records:
            if rec.state:
                state_counts[rec.state] += 1

        # Assign computed values to each record
        for record in self:
            record.total_requisitions = state_counts['total']
            record.submitted_requisition = state_counts['submitted']
            record.approved_requisition = state_counts['approved']
            record.completed_requisition = state_counts['completed']
            record.rejected_requisition = state_counts['rejected']
            record.partially_requisition = state_counts['partially']

    @api.depends('state')
    def _compute_requisition_lines(self):
        for record in self:
            record.total_lines = self.env['purchase.requisition.line'].search_count([
                ('requisition_id', '=', record.id)
            ])

    @api.depends('line_ids.approval_state')
    def _check_all_lines_completed(self):
        """Check if all product lines have approval_state = 'completed' and update state accordingly."""
        for record in self:
            if record.line_ids and all(line.approval_state == 'completed' for line in record.line_ids):
                self.state = 'completed'

    @api.depends('line_ids.approval_state', 'line_ids.picking_type')
    def _compute_all_lines_completed(self):
        for requisition in self:
            purchase_order_lines = requisition.line_ids.filtered(lambda line: line.picking_type == 'sent_rfq')
            requisition.all_lines_completed = all(
                line.approval_state == 'completed' for line in purchase_order_lines) if purchase_order_lines else False

    @api.depends('line_ids.approval_state', 'line_ids.picking_type')
    def _compute_all_internal_completed(self):
        for requisition in self:
            internal_picking_lines = requisition.line_ids.filtered(lambda line: line.picking_type == 'internal_picking')
            requisition.all_internal_completed = all(
                line.approval_state == 'completed' for line in
                internal_picking_lines) if internal_picking_lines else False

    def action_approve_line(self):
        for line in self:
            line.approval_state = 'approved'

    def action_reject_line(self):
        for line in self:
            line.approval_state = 'pending'

    @api.constrains('requisition_date', 'requisition_deadline')
    def _check_requisition_dates(self):
        for record in self:
            # Check if requisition_date is in the past
            if record.requisition_date and record.requisition_date < date.today():
                raise ValidationError("Requisition Date cannot be in the past.")

            # Check if requisition_deadline is at least 5 days after the requisition_date
            if record.requisition_date and record.requisition_deadline:
                min_deadline_date = record.requisition_date + timedelta(days=5)
                if record.requisition_deadline < min_deadline_date:
                    raise ValidationError("Requisition Deadline must be at least 5 days after the Requisition Date.")

    def action_redirect_delivery(self):
        """Create a stock picking for approved internal picking lines."""
        self.ensure_one()

        # Filter lines with picking_type = 'internal_picking' and approval_state = 'approved'
        approved_internal_lines = self.line_ids.filtered(
            lambda l: l.picking_type == 'internal_picking' and l.approval_state == 'approved'
        )

        if not approved_internal_lines:
            raise ValidationError("No approved internal picking lines available for delivery creation.")

        # Get the internal picking type
        picking_type_id = self.env.ref('stock.picking_type_internal').id

        # Create the stock picking
        stock_picking = self.env['stock.picking'].create({
            'origin': self.reference,
            'picking_type_id': picking_type_id,
            'location_id': self.internal_picking_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'requisition_id': self.id,  # Link to the current requisition
            'move_ids_without_package': [(0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
                'name': line.product_id.display_name,
                'location_id': self.internal_picking_location_id.id,
                'location_dest_id': self.destination_location_id.id,
            }) for line in approved_internal_lines]
        })

        # Update the internal picking reference and the state of approved lines
        for line in approved_internal_lines:
            line.write({
                'picking_id': stock_picking.id,  # Link the stock.picking to the requisition line
                'ref_rfq': stock_picking.name,  # Update the reference field
                'approval_state': 'completed',  # Mark the line as completed
                'status': 'draft',  # Set initial status1 to 'draft' (or the appropriate state)
            })

        self._check_all_lines_completed()

        # return {
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'stock.picking',
        #     'view_mode': 'form',
        #     'res_id': stock_picking.id,
        #     'target': 'current',
        #     'name': 'Internal Picking',
        # }

        # Return action to open the stock picking in list or form view
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Stock Picking',
        #     'res_model': 'stock.picking',
        #     'view_mode': 'list,form',
        #     'domain': [('id', '=', stock_picking.id)],
        #     'target': 'current',
        # }

    def action_redirect_to_RFQ(self):
        """Create separate RFQs for approved lines with picking_type 'sent_rfq' based on vendors."""
        self.ensure_one()

        # Filter lines with picking_type = 'sent_rfq' and approval_state = 'approved'
        requisition_lines = self.line_ids.filtered(
            lambda l: l.picking_type == 'sent_rfq' and l.approval_state == 'approved'
        )

        if not requisition_lines:
            raise ValidationError("No approved lines with 'Sent RFQ' type are available for RFQ creation.")

        # Group lines by partner_id (vendor)
        vendor_lines_map = {}
        for line in requisition_lines:
            if line.partner_id:  # Ensure the line has a vendor assigned
                vendor_lines_map.setdefault(line.partner_id.id, []).append(line)
            else:
                raise ValidationError(f"Product '{line.product_id.display_name}' does not have a vendor assigned.")

        rfq_records = []
        for partner_id, lines in vendor_lines_map.items():
            # Create RFQ order lines
            order_lines = [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
                'price_unit': line.product_id.standard_price,  # Default to standard price
                'product_uom': line.product_uom.id,
                'name': line.product_id.display_name or "No Description"
            }) for line in lines]

            # Create an RFQ for the vendor
            rfq = self.env['purchase.order'].create({
                'requisition_id': self.id,
                'partner_id': partner_id,
                'order_line': order_lines
            })
            rfq_records.append(rfq.id)

            # Attach the correct RFQ reference number to each product
            for line in lines:
                line.ref_rfq = rfq.name  # Assign RFQ reference to the specific product
                line.approval_state = 'completed'

            self._check_all_lines_completed()
        return rfq_records
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Requests for Quotation',
        #     'res_model': 'purchase.order',
        #     'view_mode': 'list,form',
        #     'domain': [('id', 'in', rfq_records)],
        #     'target': 'current',
        # }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals['reference'] == 'New':
                sequence = self.env['ir.sequence'].next_by_code('Pr.seq')
                if sequence:
                    vals['reference'] = sequence
        return super().create(vals_list)

    def action_approve(self):
        self.ensure_one()

        requisition_lines = self.line_ids.filtered(
            lambda l: l.approval_state in ('approved', 'completed')
        )

        if not requisition_lines:
            raise UserError("Approve at least one product.")

        pending_or_empty_lines = self.line_ids.filtered(
            lambda l: l.approval_state in ('pending', False, None, '')
        )

        if pending_or_empty_lines:
            self.state = 'partially'
        else:
            self.state = 'approved'

    def action_submit(self):
        self.state = 'submitted'

    def action_reject(self):
        self.state = 'rejected'


class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.requisition.line'
    _description = 'Purchase Requisition Line'

    requisition_id = fields.Many2one('employee.requisition', string='Requisition Reference', required=True,
                                     ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    picking_type = fields.Selection([
        ('sent_rfq', 'Sent RFQ'),
        ('internal_picking', 'Internal Picking')
    ], string="Requisition Action")
    picking_id = fields.Many2one('stock.picking', string='Stock Picking')  # Link to stock.picking
    status = fields.Selection([
        ('draft', 'Draft'),
        ('rfq', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('confirmed', 'Ready'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),
        ('purchase', 'Purchase Order')
    ], string='Status')
    product_qty = fields.Float(string='Quantity', required=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    ref_rfq = fields.Char(string="RFQ Reference", readonly=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        help="The vendor for this requisition."
    )
    approval_state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
    ], string="Approval State")
    picking_type = fields.Selection([
        ('sent_rfq', 'Sent RFQ'),
        ('internal_picking', 'Internal Picking')
    ], string="Requisition Action")
    forecast_availability = fields.Float(
        string='Available Quantity',
        compute='_compute_forecast_availability',
        readonly=True
    )

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
            'move_to_match_ids': self.ids,
        }

        # Customizing the warehouse context
        requisition = self.requisition_id
        if requisition:
            warehouse = requisition.destination_location_id.warehouse_id or requisition.internal_picking_location_id.warehouse_id
            if warehouse:
                action['context']['warehouse_id'] = warehouse.id

        return action

    @api.depends('product_id')
    def _compute_forecast_availability(self):
        for line in self:
            if line.product_id:
                # Fetch total available quantity directly from the product
                line.forecast_availability = line.product_id.qty_available
            else:
                line.forecast_availability = 0

    def action_approve_line(self):
        for line in self:
            line.approval_state = 'approved'

    def action_reject_line(self):
        for line in self:
            line.approval_state = 'pending'