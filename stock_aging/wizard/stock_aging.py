# -*- coding: utf-8 -*-


from odoo import models, fields, api, _


class StockAgingReportWizard(models.Model):

    _name = 'stock.aging.report.wizard'

    end_date = fields.Date(required=True)
    period_length = fields.Integer("Period Length(Days)", default=30, required=True)
    location_id = fields.Many2one(comodel_name="stock.location",
                                  string="Location", required=True)
    product_categ_id = fields.Many2one(comodel_name="product.category",
                                       string="Product Category", required=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)

    @api.multi
    def print_stock_aging_report(self):
        self.ensure_one()
        data = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        data.update({'form': res})
        # return self.env.ref('stock_aging.stock_aging_report').report_action(self, data=data)
        return self.env['ir.actions.report'].search([('report_name', '=', 'stock_aging.stock_aging_report')], limit=1).report_action(self, data=data)

    @api.multi
    def print_stock_aging_xlsx(self):
        """
         To get the date and print the report
         @return: return report
        """
        self.ensure_one()
        data = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        data.update({'form': res})
        return self.env.ref('stock_aging.stock_aging_xlsx').report_action(self, data=data)

