from odoo import api, fields, models, exceptions
from odoo.exceptions import ValidationError
from datetime import timedelta
import re
import logging

_logger = logging.getLogger(__name__)

class TicketRaise(models.Model):
    _name = "ticket.raise"
    _description = "Ticket Details"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name_id"

    name_id = fields.Many2one('erp.solution', string="Name*", required=True)
    email_id = fields.Char(string="Email Id*", required=True)
    mobile = fields.Char(string="Mobile*", required=True)
    ticket_type = fields.Selection(
        [('Question', 'Question'), ('Doubt', 'Doubt'), ('Error', 'Error'), ('Feedback', 'Feedback')],
        string='Ticket Type')
    description = fields.Text('Description*', required=True)
    attachments_id = fields.Many2many(
        comodel_name='ir.attachment',
        relation='ticket_raise_ir_attachment_rel',  # Unique table name for this many2many relationship
        column1='ticket_raise_id',  # The column in the relation table pointing to your model
        column2='attachment_id',  # The column in the relation table pointing to ir.attachment
        string="Attachments"
    )
    state = fields.Selection([
        ('nil', 'Nil'),
        ('open', 'open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], string="Status", default="nil")
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string="Priority", default='low')
    # assign_id = fields.Char(string='Assigned Developer')
    sla_deadline = fields.Datetime(string="Ticket Deadline", compute="_compute_sla_deadline", store=True)
    sla_status = fields.Selection([
        ('on_time', 'On Time'),
        ('overdue', 'Overdue'),
        ('Done', 'Done')], string="Ticket Status", compute="_compute_sla_status", store=True)
    reference = fields.Char(string="Reference", default="New", readonly=True)
    feedback_id = fields.Many2one('ticket.feedback', string='Feedback', compute='_compute_feedback_id', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super(TicketRaise, self).create(vals_list)
        for ticket in tickets:
            # Generate reference if needed
            if not ticket.reference or ticket.reference == 'New':
                sequence = self.env['ir.sequence'].next_by_code('ticket.seq')
                if sequence:
                    ticket.reference = sequence

            # Create related record in ticket.counter
            counter_record = self.env['ticket.counter'].create({
                'name_id': ticket.name_id.name,
                'email_id': ticket.email_id,
                'mobile': ticket.mobile,
                'ticket_type': ticket.ticket_type,
                'description': ticket.description,
                'attachments_id': ticket.attachments_id,
                'reference': ticket.reference,
            })

            # Schedule activity for the counter record
            counter_record.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary='Follow up on the new ticket',
                note=f'A new ticket "{ticket.name_id.name} (ID: {ticket.id})" has been created.',
            )

            template = self.env.ref('bright_information_systems.email_template_ticket_send')
            if template:
                template.send_mail(tickets.id, force_send=True)

                template = self.env.ref('bright_information_systems.email_template_ticket_send_customer')
                if template:
                    template.send_mail(tickets.id, force_send=True)

        return tickets

    @api.constrains('email_id')
    def check_email_id(self):
        for record in self:
            if record.email_id and not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", record.email_id):
                raise ValidationError('Invalid email address.')

    @api.constrains('mobile')
    def validate_mobile_number(number):
        for record in number:
            if record.mobile and not re.match(r'^\d{8}$', record.mobile):
                raise ValidationError('Invalid Mobile Number, Numbers must be 8 digits')

    @api.onchange('name_id')
    def onchange_name_id(self):
        self.email_id = self.name_id.email
        self.mobile = self.name_id.mobile_number

    @api.depends('priority', 'create_date')
    def _compute_sla_deadline(self):
        for ticket in self:
            if ticket.create_date:
                priority_mapping = {
                    'high': timedelta(days=1),
                    'medium': timedelta(days=3),
                    'low': timedelta(days=5),
                }
                ticket.sla_deadline = ticket.create_date + priority_mapping.get(ticket.priority, timedelta(days=1))
            else:
                ticket.sla_deadline = fields.Datetime.now() + timedelta(days=1)

    @api.depends('sla_deadline', 'state')
    def _compute_sla_status(self):
        for ticket in self:
            if ticket.sla_deadline and ticket.state not in ['resolved', 'closed']:
                ticket.sla_status = 'overdue' if fields.Datetime.now() > ticket.sla_deadline else 'on_time'
            else:
                ticket.sla_status = 'Done'

    def unlink(self):
        for record in self:
            if not getattr(record, '_from_counter_unlink', False):  # Skip if triggered from ticket.counter
                linked_counter = self.env['ticket.counter'].sudo().search([('reference', '=', record.reference)],
                                                                          limit=1)
                if linked_counter:
                    linked_counter.with_context(from_raise_unlink=True).unlink()
        return super(TicketRaise, self).unlink()

    def action_close_with_feedback(self):
        # Override your ticket close method to open a feedback form
        self.ensure_one()
        existing_feedback = self.env['ticket.feedback'].search([('ticket_id', '=', self.id)], limit=1)
        if existing_feedback:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Feedback',
                'view_mode': 'form',
                'res_model': 'ticket.feedback',
                'res_id': existing_feedback.id,
                'target': 'current',
            }
        else:
            return {
                'name': 'Provide Feedback',
                'view_mode': 'form',
                'res_model': 'ticket.feedback',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_ticket_id': self.id,
                },
                'target': 'new',
            }