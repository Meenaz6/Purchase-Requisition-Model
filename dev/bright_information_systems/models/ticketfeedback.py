from odoo import api, fields, models, exceptions

class TicketFeedback(models.Model):
    _name = 'ticket.feedback'
    _description = "Ticket Feedback"
    _rec_name = 'ticket_id'

    ticket_id = fields.Many2one('ticket.raise', string='Name', required=True)
    satisfaction_level = fields.Selection(
        selection=[
            ('very_satisfied', 'Very Satisfied'),
            ('satisfied', 'Satisfied'),
            ('neutral', 'Neutral'),
            ('unsatisfied', 'Unsatisfied'),
            ('very_unsatisfied', 'Very Unsatisfied')
        ],
        string='Satisfaction Level',
        required=True
    )
    resolution_quality = fields.Selection(
        selection=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('average', 'Average'),
            ('poor', 'Poor'),
            ('very_poor', 'Very Poor')
        ],
        string='Resolution Quality',
        required=True
    )
    response_speed = fields.Selection(
        selection=[
            ('fast', 'Fast'),
            ('moderate', 'Moderate'),
            ('slow', 'Slow'),
            ('very_slow', 'Very Slow')
        ],
        string='Response Speed',
        required=True
    )
    issue_relevance = fields.Boolean('Issue Addressed')
    additional_comments = fields.Text('Additional Comments')
    feedback_date = fields.Datetime(string='Feedback Date', default=fields.Datetime.now)