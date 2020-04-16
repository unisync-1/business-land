# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class Invoice(models.Model):
    _inherit = 'account.invoice'

    supply_date = fields.Date(string="Date of Supply")
    sale_warehouse_id = fields.Many2one(comodel_name="stock.warehouse",
                                        string="Store Name", readonly=True,
                                        compute="_compute_sale_warehouse_id")

    @api.multi
    def _compute_sale_warehouse_id(self):
        for invoice in self:
            if invoice.type == 'out_invoice':
                if invoice.origin:
                    sale_id = self.env['sale.order'].sudo().search([('name', '=', invoice.origin)],
                                                                        limit=1)
                    if sale_id:

                        invoice.sale_warehouse_id = sale_id.warehouse_id.id


