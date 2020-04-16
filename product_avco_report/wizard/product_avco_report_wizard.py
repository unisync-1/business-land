# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class ProductAvcoReportWizard(models.TransientModel):
    _name = "product.avco.report.wizard"

    date_to = fields.Date(string='End Date')
    location_ids = fields.Many2many(comodel_name="stock.location", string="Location", required=True,
                                  domain=[('usage', '=', 'internal')])

    @api.multi
    def print_report(self):
        """
         To get the date and print the report
         @return: return report
        """
        self.ensure_one()
        data = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        data.update({'form': res})
        return self.env.ref('product_avco_report.product_avco_report').report_action(self, data=data)

