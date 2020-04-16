# -*- coding: utf-8 -*-
{
    'name': 'Product Average Cost Report',
    'version': '1.0',
    'author': "Ejaftech",
    "description": """
    """,
    'depends': [
                'stock_account',
                'stock_landed_costs',
                'report_xlsx',
               ],
    'data': [
        'security/ir.model.access.csv',
        'report/reports.xml',
        'wizard/product_avco_report_wizard.xml',
        'views/stock_move_view.xml',

    ],

    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
