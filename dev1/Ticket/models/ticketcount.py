from pydoc import visiblename

from odoo import api, fields, models
from datetime import timedelta
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class TicketCounter(models.Model):
    _name = 'ticket.counter'
    _description = 'Ticketing System'
    _rec_name = 'name_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name_id = fields.Char(string="Name")
    email_id = fields.Char(string="Email Id")
    mobile = fields.Char(string="Mobile")
    ticket_type = fields.Selection(
        [('Question', 'Question'), ('Doubt', 'Doubt'), ('Error', 'Error'), ('Feedback', 'Feedback')],
        string='Ticket Type')
    description = fields.Text('Description')
    attachments_id = fields.Many2many(
        comodel_name='ir.attachment',
        relation='ticket_count_ir_attachment_rel',
        column1='ticket_count_id',
        column2='attachment_id', string="Attachments")
    creation_date = fields.Datetime(string='Today Date', default=fields.Datetime.now)
    assign_id = fields.Many2one('res.users',string='Assign Developer')
    reassign_id = fields.Many2one('res.users',string='Re-Assign Developer')
    description2 = fields.Text(string='Description')
    state = fields.Selection([
        ('open', 'open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')], string="Status")
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], default='low', string="Priority")
    sla_deadline = fields.Datetime(string="Ticket Deadline", compute="_compute_sla_deadline", store=True)
    sla_status = fields.Selection([
        ('on_time', 'On Time'),
        ('overdue', 'Overdue')], string="Ticket Status", compute="_compute_sla_status", store=True)
    reference = fields.Char(string="Reference", readonly=True)
    time_start = fields.Datetime(string='Start Time')
    time_end = fields.Datetime(string='End Time')
    time_spent = fields.Char(string='Time Spent', compute='_compute_time_spent', store=True)
    is_running = fields.Boolean(string='Is Running', default=False)
    estimate_time = fields.Char(string="Estimated Time",)
    re_estimated_time = fields.Char(string="Re-Estimated Time")
    total_tickets = fields.Integer(compute='_compute_ticket_count', string="Total Tickets Assigned")
    total_time = fields.Char(compute='_compute_total_time', string="Total Time Worked (Hours)")
    assigned_tickets = fields.One2many('ticket.counter', 'assign_id', string="Assigned Tickets",
                                       compute='_compute_assigned_tickets')

    @api.depends('assign_id', 'reassign_id')
    def _compute_assigned_tickets(self):
        for record in self:
            if record.assign_id:
                record.assigned_tickets = self.search(
                    ['|', ('assign_id', '=', record.assign_id.id), ('reassign_id', '=', record.assign_id.id)]
                )
            else:
                record.assigned_tickets = []

    @api.depends('reference')
    def _compute_ticket_count(self):
        for user in self:
            user.total_tickets = self.env['ticket.counter'].search_count([('assign_id', '=', user.id)])

    def action_start_time(self):
        self.time_start = fields.Datetime.now()
        self.is_running = True

    def action_stop_time(self):
        self.time_end = fields.Datetime.now()
        self.is_running = False

    def write(self, vals):
        res = super(TicketCounter, self).write(vals)
        for record in self:
            if 'state' in vals :
                linked_ticket = self.env['ticket.raise'].sudo().search([('reference', '=', record.reference)], limit=1)
                if linked_ticket:
                    linked_ticket.sudo().update({'state': vals['state']})
                    if 'priority' in vals:
                        linked_ticket = self.env['ticket.raise'].sudo().search([('reference', '=', record.reference)],                                                           limit=1)
                        if linked_ticket:
                           linked_ticket.sudo().update({'priority': vals['priority']})

        return res

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

    def _get_customer_information(self):
        return {
            'name_id': self.name_id,
            'email': self.email_id,
            'assign_id': self.assign_id.name,
            'ticket_type': self.ticket_type,
            'state': self.state,
            'sla_deadline': self.sla_deadline,
        }

    @api.depends('sla_deadline', 'state')
    def _compute_sla_status(self):
        for ticket in self:
            if ticket.sla_deadline and ticket.state not in ['resolved', 'closed']:
                ticket.sla_status = 'overdue' if fields.Datetime.now() > ticket.sla_deadline else 'on_time'
            # else:
            #     ticket.sla_status = False

    def action_ticket_send(self):
        """Opens a wizard to compose an email for ticket notifications with dynamic template selection."""
        self.ensure_one()

        # Prepare context for the email composition wizard
        ctx = {
            'default_model': 'ticket.counter',
            'default_res_ids': [self.id],  # Pass as a list
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
        }

        # Get both templates
        customer_template = self.env.ref('Ticket.email_template_ticket_notification', False)
        devop_template = self.env.ref('Ticket.email_template_ticket_devop', False)
        reassing_template = self.env.ref('Ticket.email_template_ticket_redevop', False)
        feedback_tempalte = self.env.ref('Ticket.email_template_feedback_notification', False)

        # Set the default template based on availability
        if devop_template:
            ctx.update({'default_template_id': devop_template.id})
        elif customer_template:
            ctx.update({'default_template_id': customer_template.id})
        elif reassing_template:
            ctx.update({'default_template_id': reassing_template.id})
        elif feedback_tempalte:
            ctx.update({'default_template_id': feedback_tempalte.id})

        ctx.update({'force_email': True})  # Force email sending

        # Provide options for template selection
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
        return action

    @api.depends('assign_id', 'reassign_id')
    def _compute_ticket_count(self):
        """Count the total number of tickets assigned or reassigned to a developer."""
        for record in self:
            if record.assign_id:
                # Count tickets where the developer is either assigned or reassigned
                record.total_tickets = self.search_count(
                    ['|', ('assign_id', '=', record.assign_id.id), ('reassign_id', '=', record.assign_id.id)]
                )
            else:
                record.total_tickets = 0

    @api.depends('time_start', 'time_end')
    def _compute_time_spent(self):
        """Compute time spent in HH:MM:SS format."""
        for ticket in self:
            if ticket.time_start and ticket.time_end:
                delta = ticket.time_end - ticket.time_start
                total_seconds = int(delta.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                ticket.time_spent = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                ticket.time_spent = "00:00:00"

    def _time_spent_to_seconds(self, time_spent):
        """Helper function to convert HH:MM:SS to seconds."""
        try:
            hours, minutes, seconds = map(int, time_spent.split(':'))
            return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            return 0

    @api.depends('assign_id', 'time_spent')
    def _compute_total_time(self):
        """Compute total time worked by a developer across all tickets."""
        for record in self:
            if record.assign_id:
                tickets = self.search([('assign_id', '=', record.assign_id.id)])
                total_seconds = sum(self._time_spent_to_seconds(ticket.time_spent) for ticket in tickets)
                # Convert total seconds back to HH:MM:SS format
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                record.total_time = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                record.total_time = "00:00:00"

    def unlink(self):
        for record in self:
            if not self.env.context.get('from_raise_unlink'):  # Skip if triggered from ticket.raise
                linked_ticket = self.env['ticket.raise'].sudo().search([('reference', '=', record.reference)], limit=1)
                if linked_ticket:
                    linked_ticket.with_context(from_counter_unlink=True).unlink()
        return super(TicketCounter, self).unlink()