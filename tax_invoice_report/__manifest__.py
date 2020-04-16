# -*- coding: utf-8 -*-
{
    'name': 'Tax Invoice Report',
    'depends': [
        'sale', 'account_accountant',
    ],
    'author': "Ejaftech",
    'description': """
    """,
    'data': [
        'views/invoice_view.xml',
        'views/reports.xml',
        'report/report_tax_invoice.xml',

    ],
    'installable': True,
}