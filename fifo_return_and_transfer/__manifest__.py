# -*- coding: utf-8 -*-

{
    "name": "FIFO - Return Products And Receive In New Location",
    "version": "12.0",
    'author': "Ejaftech",
    'license': 'AGPL-3',
    'depends': ['purchase', 'stock_account'],
    'category': 'stock',
    "description": """
    """,
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/setting_view.xml',
        'views/transfer_over_location.xml',
    ],
    'installable': True,
    'auto_install': False,
}

