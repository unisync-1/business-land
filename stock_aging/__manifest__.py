# -*- coding: utf-8 -*-

{
    "name": "Stock Aging",
    "version": "12.0",
    'author': "Ejaftech",
    'license': 'AGPL-3',
    'depends': ['stock', 'report_xlsx'],
    'category': 'stock',
    "description": """
    """,
    'data': [
        'security/ir.model.access.csv',
        'report/stock_aging_report.xml',
        'wizard/stock_aging_view.xml',
        'views/report.xml',
    ],
    'installable': True,
    'auto_install': False,
}

