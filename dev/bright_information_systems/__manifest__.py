{
    'name': 'Bright',
    'version': '1.0',
    'author': 'Minhaj',
    'category': 'Bright',
    'website': 'www.erpbright.com',
    'license': 'LGPL-3',
    'sequence': '-2',
    'summary': 'We are here to manage ERP solutions from Bright Information Systems',
    'depends': ['base', 'sale', 'board', 'account', 'mail', 'crm', 'web', 'project', 'bus'],
    'assets': {
        'web.assets_backend': [
            'bright_information_systems/static/src/css/style.css',
        ],
    },
    'installable': True,
    'application': True,
    'data': [
        'security/ir.model.access.csv',
        'views/ERP.xml',
        'views/Mop.xml',
        'views/ticketraise.xml',
        'views/To_do.xml',
        'data/sequence.xml',
        'views/menu.xml',
        'data/template.xml',
        'data/automatic_email.xml',
        'reports/ticket_report_action.xml',
        'reports/customerreport.xml',
        'views/feedback.xml',
    ]
}
