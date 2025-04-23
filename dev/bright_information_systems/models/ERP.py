from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import ValidationError
import re
import logging
_logger = logging.getLogger(__name__)

class ErpSolutions(models.Model):
    _name = 'erp.solution'
    _description = 'Client Details'

    reference = fields.Char(string="Reference", default="New", readonly=True)
    name: object = fields.Char(string="Name", required=True)
    mobile_number = fields.Char(string="Mobile")
    gender = fields.Selection([('Male', 'Male'), ('Female', 'Female')], string='Gender')
    date_of_birth = fields.Date(string="Date of Birth")
    age = fields.Integer(string="Age", compute="_compute_age", store=True, readonly=False)
    email = fields.Char(string="Email")
    needed = fields.Selection([('erp solutions', 'ERP Solutions'), ('service management', 'Service Management'), ('it services', 'IT Services'), ('implementation services', 'Implementation Services')],
                              string='Select Category')
    company = fields.Char(string='Company Name')
    locate = fields.Selection(
        [('Qatar', 'Qatar'), ('India', 'India'), ('Egypt', 'Egypt'), ('Saudi Arabia', 'Saudi Arabia'),
         ('Dubai', 'Dubai')], string='Country')
    refer = fields.Selection([('Mr Isham', 'Mr Isham'), ('Mr Kareem', 'Mr Kareem'), ('Mr Abdul Azeez', 'Mr Abdul Azeez')],
                             string='Referred by')
    notes = fields.Text(string="Other details")
    ticket_id = fields.One2many('ticket.raise', 'name_id', string="Ticket")
    Invoice_id = fields.Many2many('account.move', 'partner_id', string='Invoice')
    active = fields.Boolean(string="Active", default=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')
    ], string="Priority")
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('Started', 'Started'),
        ('In process', 'In process'),
        ('Completed', 'Completed')
    ], string="Status", default="Draft", required=True)
    Information = fields.Text(string="Information")
    Hide_invoice = fields.Boolean(string="Hide Invoice ")
    image = fields.Image(string="Image")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals['reference'] == 'New':
                sequence = self.env['ir.sequence'].next_by_code('Client.seq')
                if sequence:
                    vals['reference'] = sequence
        return super().create(vals_list)

    @api.constrains('mobile_number')
    def validate_mobile_number(number):
        for record in number:
            if record.mobile_number and not re.match(r'^\d{8}$', record.mobile_number):
                raise ValidationError('Invalid Mobile Number, Numbers must be 8 digits')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for rec in self:
            today = date.today()
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year
            else:
                rec.age = 0

    def unlink(self):
        for rec in self:
            domain = [('name_id', '=', rec.id)]
            tickets = self.env['ticket.raise'].search(domain)
            if tickets:
                raise ValidationError(_("Hey! This guy %s has a ticket.\nYou can't delete it.") % rec.name)
        return super().unlink()

    @api.constrains('email')
    def _check_email(self):
        for record in self:
            if record.email and not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", record.email):
                raise ValidationError('Invalid email address.')
