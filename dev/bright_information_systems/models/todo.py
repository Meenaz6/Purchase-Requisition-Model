from odoo import api, fields, models


class Todoupdate(models.Model):
    _inherit = "project.task"

    work_link = fields.Char(string="External Work Link")
    url_selection = fields.Selection(
        [
            ('Invoicing', 'Invoicing'),
            ('Sales', 'Sales'),
            ('CRM', 'CRM'),
            ('Point of Sale', 'Point of Sale'),
            ('Project', 'Project'),
            ('Contacts', 'Contacts'),
            ('Calendar', 'Calendar'),
            ('Discuss', 'Discuss'),
            ('Email Marketing', 'Email Marketing'),
            ('Surveys', 'Surveys'),
            ('Purchase', 'Purchase'),
            ('Inventory', 'Inventory'),
            ('Employees', 'Employees'),
            ('Link Tracker', 'Link Tracker'),
            ('Apps', 'Apps'),
        ],
        string='Work'
    )

    def get_redirect_url(self):
        url_mapping = {
            'Invoicing': 'http://localhost:8010/odoo/invoicing',
            'Sales': 'http://localhost:8010/odoo/sales',
            'CRM': 'http://localhost:8010/odoo/crm',
            'Point of Sale': 'http://localhost:8010/odoo/point-of-sale',
            'Project': 'http://localhost:8010/odoo/project',
            'Contacts': 'http://localhost:8010/odoo/contacts',
            'Calendar': 'http://localhost:8010/odoo/calendar',
            'Discuss': 'http://localhost:8010/odoo/discuss',
            'BIS': 'http://localhost:8010/odoo/action-493',
            'Email Marketing': 'http://localhost:8010/odoo/email-marketing',
            'Surveys': 'http://localhost:8010/odoo/surveys',
            'Purchase': 'http://localhost:8010/odoo/purchase',
            'Inventory': 'http://localhost:8010/odoo/inventory',
            'Employees': 'http://localhost:8010/odoo/employees',
            'Link Tracker': 'http://localhost:8010/odoo/action-360',
            'Apps': 'http://localhost:8010/odoo/apps',
        }
        return url_mapping.get(self.url_selection)

    def action_redirect(self):
        redirect_url = self.get_redirect_url()
        return {
            'type': 'ir.actions.act_url',
            'url': redirect_url,
            'target': 'new',
        }


    def action_todo_ticket(self):
        """Opens a wizard to compose an email for ticket notifications with dynamic values."""
        self.ensure_one()
        # Prepare context for the email composition wizard
        ctx = {
            'default_model': 'project.task',
            'default_res_ids': self.ids,  # For single record
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
        }

        # Find the email template
        mail_template = self._find_mail_template()
        if mail_template:
            ctx.update({
                'default_template_id': mail_template.id,  # Use the template for dynamic values
                'force_email': True,
            })

        # Open the email composition wizard
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

    def _find_mail_template(self):
        """Find the email template for ticket notifications."""
        return self.env.ref('bright_information_systems.mail_template_todo', False)
