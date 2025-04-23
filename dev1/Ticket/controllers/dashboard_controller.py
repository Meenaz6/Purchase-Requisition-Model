from odoo import http
from odoo.http import request
import json

class TicketDashboard(http.Controller):
    @http.route('/ticket/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        # Get ticket data from the model
        Ticket = request.env['ticket.counter']
        
        # Calculate metrics
        total_tickets = Ticket.search_count([])
        open_tickets = Ticket.search_count([('state', '=', 'open')])
        resolved_tickets = Ticket.search_count([('state', 'in', ['resolved', 'closed'])])
        high_priority = Ticket.search_count([('priority', '=', 'high')])
        
        # Get ticket types distribution
        ticket_types = Ticket.read_group(
            [], ['ticket_type'], ['ticket_type']
        )
        
        # Get status distribution
        status_data = Ticket.read_group(
            [], ['state'], ['state']
        )
        
        # Get developer workload
        dev_workload = Ticket.read_group(
            [], ['assign_id'], ['assign_id']
        )
        
        return {
            'metrics': {
                'total_tickets': total_tickets,
                'open_tickets': open_tickets,
                'resolved_tickets': resolved_tickets,
                'high_priority': high_priority,
            },
            'charts': {
                'ticket_types': ticket_types,
                'status_data': status_data,
                'dev_workload': dev_workload,
            }
        }
